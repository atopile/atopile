"""
Logging infrastructure for atopile builds.

Provides SQLite-based structured logging, Rich console output, and audience
classification.
"""

from __future__ import annotations

import atexit
import io
import json
import logging
import os
import sys
import threading
import time
import traceback
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from enum import Enum
from pathlib import Path
from types import ModuleType, TracebackType
from typing import Any

import atopile
import faebryk
from atopile.dataclasses import (
    Log,
    LogRow,
    TestLogRow,
)
from atopile.errors import UserPythonModuleError, _BaseBaseUserException
from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.text import Text
from rich.traceback import Traceback

from atopile.logging_utils import (
    LEVEL_STYLES,
    PLOG,
    console,
    error_console,
)

# Suppress noisy third-party loggers
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Use parent's timestamp if running as parallel worker
NOW = os.environ.get("ATO_BUILD_TIMESTAMP") or datetime.now().strftime(
    "%Y-%m-%d_%H-%M-%S"
)
_DEFAULT_FORMATTER = logging.Formatter("%(message)s", datefmt="[%X]")
_log_sink_var: ContextVar[io.StringIO | None] = ContextVar("log_sink", default=None)
_log_scope_level: ContextVar[int] = ContextVar("log_scope_level", default=0)

# Custom log level
ALERT = logging.INFO + 5
logging.addLevelName(ALERT, "ALERT")

# Level conversion lookup
_LEVEL_MAP = {
    logging.DEBUG: Log.Level.DEBUG,
    logging.INFO: Log.Level.INFO,
    logging.WARNING: Log.Level.WARNING,
    logging.ERROR: Log.Level.ERROR,
    logging.CRITICAL: Log.Level.ERROR,
}


def _is_serving() -> bool:
    """Check if we're running the server."""
    main = sys.modules.get("__main__")
    return (
        "serve" in sys.argv
        or "atopile.server" in sys.argv
        or (main is not None and main.__package__ == "atopile.server")
    )




class AtoLogger(logging.Logger):
    """Logger with custom alert level."""

    def alert(self, msg: object, *args, **kwargs) -> None:
        """Log at ALERT level (between WARNING and ERROR)."""
        if self.isEnabledFor(ALERT):
            self._log(ALERT, msg, args, **kwargs)


logging.setLoggerClass(AtoLogger)

# =============================================================================
# Structured Traceback Extraction
# =============================================================================


def _get_pretty_repr(value: object, max_len: int = 200) -> str:
    """Get pretty repr using __pretty_repr__ or __rich_repr__ or fallback to repr."""
    try:
        # Try pretty_repr first (faebryk convention)
        if hasattr(value, "pretty_repr"):
            result = str(value.pretty_repr())
            return result[:max_len] + "..." if len(result) > max_len else result

        # Try __rich_repr__ (Rich library protocol)
        if hasattr(value, "__rich_repr__"):
            type_name = type(value).__name__
            rich_repr_parts = []
            for item in value.__rich_repr__():
                if isinstance(item, tuple):
                    if len(item) == 2:
                        key, val = item
                        if key is None:
                            rich_repr_parts.append(repr(val))
                        else:
                            rich_repr_parts.append(f"{key}={val!r}")
                    elif len(item) == 1:
                        rich_repr_parts.append(repr(item[0]))
                else:
                    rich_repr_parts.append(repr(item))
            result = f"{type_name}({', '.join(rich_repr_parts)})"
            return result[:max_len] + "..." if len(result) > max_len else result

        # Fallback to repr
        result = repr(value)
        return result[:max_len] + "..." if len(result) > max_len else result
    except Exception:
        return "<unable to represent>"


def _serialize_local_var(
    value: object,
    max_repr_len: int = 200,
    max_container_items: int = 50,
    depth: int = 0,
) -> dict:
    """
    Safely serialize a local variable for JSON storage.

    Containers (dict, list, set, tuple) are serialized recursively with their
    structure preserved. Non-container values use pretty_repr/repr for display.
    """
    type_name = type(value).__name__
    max_depth = 5  # Prevent infinite recursion

    # JSON-native primitives
    if isinstance(value, (bool, int, float, type(None))):
        return {"type": type_name, "value": value}

    if isinstance(value, str):
        # Truncate long strings
        if len(value) > max_repr_len:
            return {
                "type": type_name,
                "value": value[:max_repr_len] + "...",
                "truncated": True,
            }
        return {"type": type_name, "value": value}

    # Handle containers recursively (if not too deep)
    if depth < max_depth:
        if isinstance(value, dict):
            items = list(value.items())[:max_container_items]
            serialized = {}
            for k, v in items:
                # Keys must be strings for JSON
                key_str = str(k) if not isinstance(k, str) else k
                serialized[key_str] = _serialize_local_var(
                    v, max_repr_len, max_container_items, depth + 1
                )
            result: dict[str, Any] = {
                "type": "dict",
                "value": serialized,
                "length": len(value),
            }
            if len(value) > max_container_items:
                result["truncated"] = True
            return result

        if isinstance(value, (list, tuple)):
            items = list(value)[:max_container_items]
            serialized_items = [
                _serialize_local_var(item, max_repr_len, max_container_items, depth + 1)
                for item in items
            ]
            result = {
                "type": type_name,
                "value": serialized_items,
                "length": len(value),
            }
            if len(value) > max_container_items:
                result["truncated"] = True
            return result

        if isinstance(value, (set, frozenset)):
            items = list(value)[:max_container_items]
            serialized_items = [
                _serialize_local_var(item, max_repr_len, max_container_items, depth + 1)
                for item in items
            ]
            result = {
                "type": type_name,
                "value": serialized_items,
                "length": len(value),
            }
            if len(value) > max_container_items:
                result["truncated"] = True
            return result

    # For non-containers or deep nesting, use pretty repr
    repr_str = _get_pretty_repr(value, max_repr_len)
    return {"type": type_name, "repr": repr_str}


def _extract_traceback_frames(
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_tb: TracebackType | None,
    max_frames: int = 50,
    max_locals: int = 20,
    max_repr_len: int = 200,
    suppress_paths: list[str] | None = None,
) -> dict:
    """
    Extract structured traceback with local variables for the `python_traceback` field.

    This returns structured JSON data for programmatic debugging. The separate
    `ato_traceback` field (from `render_ato_traceback()`) stores ANSI-formatted
    user-friendly source snippets.

    Returns a dict with:
    - exc_type: Exception type name
    - exc_message: Exception message
    - frames: List of stack frame dicts, each containing:
      - filename: Source file path
      - lineno: Line number
      - function: Function name
      - code_line: Source code line if available
      - locals: Dict of local variables
    """
    frames = []
    tb = exc_tb
    frame_count = 0

    while tb is not None and frame_count < max_frames:
        frame = tb.tb_frame
        filename = frame.f_code.co_filename

        # Skip suppressed modules (pytest internals, etc.)
        if suppress_paths and any(p in filename for p in suppress_paths):
            tb = tb.tb_next
            continue

        # Capture locals safely
        locals_dict = {}
        try:
            for name, value in list(frame.f_locals.items())[:max_locals]:
                if name.startswith("__"):
                    continue
                locals_dict[name] = _serialize_local_var(value, max_repr_len)
        except Exception:
            pass  # Skip locals if we can't access them

        # Get source line
        code_line = None
        try:
            import linecache

            code_line = linecache.getline(filename, tb.tb_lineno).strip()
        except Exception:
            pass

        frames.append(
            {
                "filename": filename,
                "lineno": tb.tb_lineno,
                "function": frame.f_code.co_name,
                "code_line": code_line,
                "locals": locals_dict,
            }
        )

        tb = tb.tb_next
        frame_count += 1

    return {
        "exc_type": exc_type.__name__ if exc_type else "Unknown",
        "exc_message": str(exc_value) if exc_value else "",
        "frames": frames,
    }


# =============================================================================
# Log appender singletons
# =============================================================================


def _normalize_db_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


def _serialize_objects(objects: dict | None) -> str | None:
    if objects is None:
        return None
    try:
        return json.dumps(objects)
    except TypeError:
        return json.dumps({"repr": _get_pretty_repr(objects)})


# =============================================================================
# Loggers
# =============================================================================


def get_exception_display_message(exc: BaseException) -> str:
    """Get display message for exception."""
    if isinstance(exc, _BaseBaseUserException):
        return exc.message or str(exc) or type(exc).__name__
    return str(exc) or type(exc).__name__


def render_ato_traceback(exc: BaseException) -> str | None:
    """
    Render exception's rich output to an ANSI-formatted string for database storage.

    This is for the `ato_traceback` field - user-friendly source snippets with colors.
    The separate `python_traceback` field stores structured JSON from
    `_extract_traceback_frames()` for programmatic debugging.

    Uses force_terminal=True to include ANSI escape codes (colors) in the output,
    which can be rendered by the frontend.
    """
    if not hasattr(exc, "__rich_console__"):
        return None
    try:
        ansi_buffer = io.StringIO()
        capture_console = Console(
            file=ansi_buffer,
            width=120,
            force_terminal=True,  # Include ANSI color codes in output
        )
        # Skip first renderable (title) - we use it as the message
        renderables = exc.__rich_console__(capture_console, capture_console.options)
        for renderable in list(renderables)[1:]:
            capture_console.print(renderable)
        result = ansi_buffer.getvalue().strip()
        return result or None
    except Exception:
        return None


@contextmanager
def capture_logs():
    """Context manager to capture logs to a StringIO."""
    old = _log_sink_var.get()
    _log_sink_var.set(io.StringIO())
    sink = _log_sink_var.get()
    assert sink is not None
    yield sink
    _log_sink_var.set(old)


@contextmanager
def log_exceptions(log_sink: io.StringIO):
    """Context manager to capture exceptions to a log sink."""
    exc_console = Console(file=log_sink)
    exc_handler = LogHandler(console=exc_console)
    logger.addHandler(exc_handler)
    try:
        yield
    except Exception as exc:
        logger.error(exc, exc_info=exc)
        raise
    finally:
        logger.removeHandler(exc_handler)


@contextmanager
def scope(msg: str | None = None):
    """
    Context manager for hierarchical log scoping.

    Increments the global scope level on entry, decrements on exit.
    All log messages within the scope will be prefixed with '·' characters
    indicating their nesting depth, enabling tree visualization in the UI.

    Usage:
        with logging.scope("Processing items"):
            log.info("Item 1")  # Will be prefixed with '·'
            with logging.scope("Sub-processing"):
                log.info("Detail")  # Will be prefixed with '··'
    """
    current = _log_scope_level.get()
    _log_scope_level.set(current + 1)
    try:
        if msg:
            # Log the scope message at the parent level (before increment takes effect)
            # We temporarily decrement to log at parent level
            _log_scope_level.set(current)
            logger.debug(msg)
            _log_scope_level.set(current + 1)
        yield
    finally:
        _log_scope_level.set(current)


def get_scope_level() -> int:
    """Get the current log scope nesting level."""
    return _log_scope_level.get()


def _get_log_handler() -> "LogHandler | None":
    """Get the LogHandler from the root logger, if present."""
    for h in logging.getLogger().handlers:
        if isinstance(h, LogHandler):
            return h
    return None


class BaseLogger:
    """Base for structured database loggers."""

    BATCH_SIZE = 300
    FLUSH_INTERVAL = 0.5

    def __init__(self, identifier: str, context: str = ""):
        self._identifier = identifier
        self._context = context
        self._append_chunk: Callable[[list[Any]], None] | None = None
        self._buffer: list[Any] = []
        self._buffer_lock = threading.Lock()
        self._last_flush = time.monotonic()
        self._closed = False

    # Static methods for backward compatibility
    capture_logs = staticmethod(capture_logs)
    log_exceptions = staticmethod(log_exceptions)
    get_exception_display_message = staticmethod(get_exception_display_message)

    @classmethod
    def get_log_db(cls) -> Path:
        raise NotImplementedError

    def set_context(self, context: str) -> None:
        self._context = context

    def set_writer(self, writer: Callable[[list[Any]], None]) -> None:
        self._append_chunk = writer

    def log(
        self,
        level: Log.Level,
        message: str,
        *,
        logger_name: str = "",
        audience: Log.Audience = Log.Audience.DEVELOPER,
        source_file: str | None = None,
        source_line: int | None = None,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
        objects: dict | None = None,
    ) -> None:
        """Log a structured message to the database."""
        if self._append_chunk is None or self._closed:
            return

        entry = self._build_entry(
            level=level,
            message=message,
            logger_name=logger_name,
            audience=audience,
            source_file=source_file,
            source_line=source_line,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
            objects=objects,
        )
        self._append(entry)

    def _append(self, entry: Any) -> None:
        with self._buffer_lock:
            self._buffer.append(entry)
            should_flush = (
                len(self._buffer) >= self.BATCH_SIZE
                or (time.monotonic() - self._last_flush) > self.FLUSH_INTERVAL
            )
        if should_flush:
            self.flush()

    def debug(
        self,
        message: str,
        *,
        logger_name: str = "",
        audience: Log.Audience = Log.Audience.DEVELOPER,
        objects: dict | None = None,
    ) -> None:
        self.log(Log.Level.DEBUG, message, logger_name=logger_name, audience=audience, objects=objects)

    def info(
        self,
        message: str,
        *,
        logger_name: str = "",
        audience: Log.Audience = Log.Audience.DEVELOPER,
        objects: dict | None = None,
    ) -> None:
        self.log(Log.Level.INFO, message, logger_name=logger_name, audience=audience, objects=objects)

    def warning(
        self,
        message: str,
        *,
        logger_name: str = "",
        audience: Log.Audience = Log.Audience.DEVELOPER,
        objects: dict | None = None,
    ) -> None:
        self.log(Log.Level.WARNING, message, logger_name=logger_name, audience=audience, objects=objects)

    def error(
        self,
        message: str,
        *,
        logger_name: str = "",
        audience: Log.Audience = Log.Audience.DEVELOPER,
        objects: dict | None = None,
    ) -> None:
        self.log(Log.Level.ERROR, message, logger_name=logger_name, audience=audience, objects=objects)

    def flush(self) -> None:
        if self._append_chunk is None:
            return
        with self._buffer_lock:
            if not self._buffer:
                return
            entries, self._buffer = self._buffer, []
            self._last_flush = time.monotonic()
        try:
            self._append_chunk(entries)
        except Exception:
            pass

    def close(self) -> None:
        self._closed = True
        self.flush()

    def _build_entry(
        self,
        *,
        level: Log.Level,
        message: str,
        logger_name: str,
        audience: Log.Audience,
        source_file: str | None,
        source_line: int | None,
        ato_traceback: str | None,
        python_traceback: str | None,
        objects: dict | None,
    ) -> LogRow | TestLogRow:
        raise NotImplementedError


class LoggerForTest(BaseLogger):
    """Test log database interface."""

    @staticmethod
    def get_log_db() -> Path:
        from faebryk.libs.paths import get_log_dir

        return get_log_dir() / "test_logs.db"

    @classmethod
    def close_all(cls) -> None:
        if (h := _get_log_handler()) and h._test_logger:
            h._test_logger.close()

    @classmethod
    def flush_all(cls) -> None:
        """Flush pending logs without closing the writer."""
        if (h := _get_log_handler()) and h._test_logger:
            h._test_logger.flush()

    @classmethod
    def setup_logging(cls, test_run_id: str, test: str = "") -> "LoggerForTest | None":
        try:
            from atopile.model.sqlite import TestLogs

            TestLogs.init_db()
            TestLogs.register_run(test_run_id)

            test_logger = cls(test_run_id, test)
            test_logger.set_writer(TestLogs.append_chunk)
            if h := _get_log_handler():
                h._test_logger = test_logger
            return test_logger
        except Exception:
            return None

    @classmethod
    def update_test_name(cls, test: str | None) -> None:
        if (h := _get_log_handler()) and h._test_logger:
            h._test_logger.set_context(test or "")

    @property
    def test_run_id(self) -> str:
        return self._identifier

    def set_test(self, test: str) -> None:
        self.set_context(test)

    def _build_entry(
        self,
        level: Log.Level,
        message: str,
        logger_name: str,
        audience: Log.Audience,
        source_file: str | None,
        source_line: int | None,
        ato_traceback: str | None,
        python_traceback: str | None,
        objects: dict | None,
    ) -> TestLogRow:
        return TestLogRow(
            test_run_id=self._identifier,
            timestamp=datetime.now().isoformat(),
            test_name=self._context,
            level=_normalize_db_value(level),
            logger_name=logger_name,
            message=message,
            audience=_normalize_db_value(audience),
            source_file=source_file,
            source_line=source_line,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
            objects=_serialize_objects(objects),
        )


class BuildLogger(BaseLogger):
    """Build log database interface."""

    _loggers: dict[str, "BuildLogger"] = {}

    @staticmethod
    def get_log_db() -> Path:
        from faebryk.libs.paths import get_log_dir

        return get_log_dir() / "build_logs.db"

    @classmethod
    def get(
        cls,
        project_path: str,
        target: str,
        timestamp: str | None = None,
        stage: str = "",
        build_id: str | None = None,
    ) -> "BuildLogger":
        timestamp = timestamp or NOW
        from atopile.model.sqlite import Logs

        Logs.init_db()

        if build_id is None:
            from atopile.buildutil import generate_build_id

            build_id = generate_build_id(project_path, target, timestamp)
        if build_id not in cls._loggers:
            bl = cls(build_id, stage)
            bl.set_writer(Logs.append_chunk)
            cls._loggers[build_id] = bl
        else:
            cls._loggers[build_id].set_context(stage)
        return cls._loggers[build_id]

    @classmethod
    def close_logger(cls, build_id: str) -> None:
        if build_id in cls._loggers:
            cls._loggers.pop(build_id).close()

    @classmethod
    def close_all(cls) -> None:
        for bid in list(cls._loggers):
            cls.close_logger(bid)

    @classmethod
    def setup_logging(
        cls, enable_database: bool = True, stage: str | None = None
    ) -> "BuildLogger | None":
        if not enable_database:
            return None
        try:
            from atopile.config import config

            try:
                project_path = str(config.project.paths.root.resolve())
                target = config.build.name if hasattr(config, "build") else "cli"
            except (RuntimeError, AttributeError):
                project_path, target = "cli", "default"

            env_build_id = os.environ.get("ATO_BUILD_ID")
            env_timestamp = os.environ.get("ATO_BUILD_TIMESTAMP")
            if not env_build_id or not env_timestamp:
                return None

            bl = cls.get(
                project_path,
                target,
                timestamp=env_timestamp,
                stage=stage or "cli",
                build_id=env_build_id,
            )
            if h := _get_log_handler():
                h._build_logger = bl
            return bl
        except Exception:
            return None

    @classmethod
    def update_stage(cls, stage: str | None) -> None:
        if (h := _get_log_handler()) and h._build_logger:
            h._build_logger.set_context(stage or "")
            if stage:
                logging.getLogger(__name__).debug(f"Starting build stage: {stage}")

    def set_stage(self, stage: str) -> None:
        self.set_context(stage)

    @property
    def build_id(self) -> str:
        return self._identifier

    def _build_entry(
        self,
        level: Log.Level,
        message: str,
        logger_name: str,
        audience: Log.Audience,
        source_file: str | None,
        source_line: int | None,
        ato_traceback: str | None,
        python_traceback: str | None,
        objects: dict | None,
    ) -> LogRow:
        return LogRow(
            build_id=self._identifier,
            timestamp=datetime.now().isoformat(),
            stage=self._context,
            level=_normalize_db_value(level),
            logger_name=logger_name,
            message=message,
            audience=_normalize_db_value(audience),
            source_file=source_file,
            source_line=source_line,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
            objects=_serialize_objects(objects),
        )

    def exception(
        self,
        exc: BaseException,
        *,
        audience: Log.Audience = Log.Audience.DEVELOPER,
        level: Log.Level = Log.Level.ERROR,
    ) -> None:
        message = str(exc) or type(exc).__name__
        ato_tb = render_ato_traceback(exc)
        python_tb = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        self.log(
            level,
            message,
            audience=audience,
            ato_traceback=ato_tb,
            python_traceback=python_tb,
        )


# =============================================================================
# Rich Log Handler
# =============================================================================


class LogHandler(RichHandler):
    """Rich logging handler with database support."""

    def __init__(
        self,
        *args,
        console: Console,
        rich_tracebacks: bool = True,
        show_path: bool = False,
        tracebacks_suppress: Iterable[str] | None = None,
        tracebacks_suppress_map: (
            dict[type[BaseException], Iterable[ModuleType]] | None
        ) = None,
        tracebacks_unwrap: list[type[BaseException]] | None = None,
        hide_traceback_types: tuple[type[BaseException], ...] | None = None,
        always_show_traceback_types: tuple[type[BaseException], ...] = (
            UserPythonModuleError,
        ),
        traceback_level: int = logging.ERROR,
        force_terminal: bool = False,
        build_logger: BuildLogger | None = None,
        **kwargs,
    ):
        super().__init__(
            *args,
            console=console,
            rich_tracebacks=rich_tracebacks,
            show_path=show_path,
            show_time=False,
            show_level=False,
            **kwargs,
        )
        self.tracebacks_suppress = list(tracebacks_suppress or ["typer"])
        self.tracebacks_suppress_map = tracebacks_suppress_map or {
            UserPythonModuleError: [atopile, faebryk]
        }
        self.tracebacks_unwrap = tracebacks_unwrap or [UserPythonModuleError]
        if hide_traceback_types is None:
            from atopile.compiler import DslRichException

            hide_traceback_types = (_BaseBaseUserException, DslRichException)
        self.hide_traceback_types = hide_traceback_types
        self.always_show_traceback_types = always_show_traceback_types
        self.traceback_level = traceback_level
        self._is_terminal = force_terminal or console.is_terminal
        self._build_logger = build_logger
        self._test_logger: LoggerForTest | None = None

    def _get_suppress(
        self, exc_type: type[BaseException] | None
    ) -> list[str | ModuleType]:
        suppress: set[str | ModuleType] = set(self.tracebacks_suppress)
        if exc_type:
            for t, mods in self.tracebacks_suppress_map.items():
                if issubclass(exc_type, t) or isinstance(exc_type, t):
                    suppress.update(mods)
        return list(suppress)

    def _unwrap_chain(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> tuple[type[BaseException] | None, BaseException | None, TracebackType | None]:
        if exc_type and exc_value:
            while any(issubclass(exc_type, t) for t in self.tracebacks_unwrap):
                while isinstance(exc_value, exc_type) and exc_value.__cause__:
                    exc_value = exc_value.__cause__
                exc_type = type(exc_value)
                exc_tb = exc_value.__traceback__
        return exc_type, exc_value, exc_tb

    def _get_traceback(self, record: logging.LogRecord) -> Traceback | None:
        if not record.exc_info:
            return None
        exc_type, exc_value, exc_tb = record.exc_info
        if isinstance(exc_value, UserPythonModuleError):
            exc_type, exc_value, exc_tb = self._unwrap_chain(
                exc_type, exc_value, exc_tb
            )
        is_hidden_type = isinstance(
            exc_value, self.hide_traceback_types
        ) and not isinstance(exc_value, self.always_show_traceback_types)
        hide = is_hidden_type or record.levelno < self.traceback_level
        if hide or not exc_type or not exc_value:
            return None

        # Use console width or None (unlimited) to avoid truncating tracebacks
        width = getattr(self, "tracebacks_width", None) or getattr(
            self.console, "width", None
        )
        # If width is None, Rich will use full available width

        return Traceback.from_exception(
            exc_type,
            exc_value,
            exc_tb,
            width=width,
            extra_lines=getattr(self, "tracebacks_extra_lines", 3),
            theme=getattr(self, "tracebacks_theme", None),
            word_wrap=getattr(self, "tracebacks_word_wrap", True),
            show_locals=getattr(self, "tracebacks_show_locals", False),
            locals_max_length=getattr(self, "locals_max_length", 10),
            locals_max_string=getattr(self, "locals_max_string", 80),
            max_frames=getattr(
                self, "tracebacks_max_frames", 100
            ),  # Reduced from 1000 - syntax highlighting is slow with many frames
            suppress=self._get_suppress(exc_type),
        )

    def _render_message(
        self, record: logging.LogRecord, message: str
    ) -> "ConsoleRenderable":
        """Render message text in to Text.

        Args:
            record (LogRecord): logging Record.
            message (str): String containing log message.

        Returns:
            ConsoleRenderable: Renderable to display log message.
        """
        # Check if message contains ANSI escape codes (from rich_to_string tables, etc.)
        # ANSI codes start with ESC[ which is \x1b[ or \033[
        has_ansi = "\x1b[" in message or "\033[" in message

        # If message has ANSI codes, parse them to render properly
        # This handles output from rich_to_string() which includes ANSI styling
        if has_ansi:
            return Text.from_ansi(message)

        if not self._is_terminal:
            return Text(message)
        use_markdown = getattr(record, "markdown", False)
        use_markup = getattr(record, "markup", self.markup)
        if use_markdown:
            return Markdown(message)
        msg_text = Text.from_markup(message) if use_markup else Text(message)
        if hl := getattr(record, "highlighter", self.highlighter):
            msg_text = hl(msg_text)
        if kw := (self.keywords or self.KEYWORDS):
            msg_text.highlight_words(kw, "logging.keyword")
        return msg_text

    def render_message(
        self, record: logging.LogRecord, message: str
    ) -> ConsoleRenderable:
        if record.exc_info and (exc := record.exc_info[1]):
            if isinstance(exc, ConsoleRenderable) or hasattr(exc, "__rich_console__"):
                return exc  # type: ignore

        from datetime import datetime

        # Build styled prefix: time, level, logger name with consistent background
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level_name = record.levelname
        logger_name = record.name

        # Truncate/pad logger name to fixed width (25 chars) for alignment
        if len(logger_name) > 25:
            logger_name = "…" + logger_name[-24:]
        logger_name = f"{logger_name:<25}"

        # Level-specific colors (from shared constants)
        level_color = LEVEL_STYLES.get(level_name, "white")

        # Use dim styling which adapts to light/dark terminals
        prefix = Text()
        prefix.append(f"{timestamp} ", style="dim")
        prefix.append(f"{level_name:<8}", style=level_color)
        prefix.append(f" {logger_name:<25} ", style="dim")
        prefix.append(" ", style="default")  # Space separator instead of divider

        # Combine with message
        msg_renderable = self._render_message(record, message)
        if isinstance(msg_renderable, Text):
            return prefix + msg_renderable
        return msg_renderable

    def _write_to_db(self, record: logging.LogRecord) -> None:
        if _is_serving():
            return
        for db_logger in (self._build_logger, self._test_logger):
            if db_logger is None:
                continue
            try:
                level = _LEVEL_MAP.get(record.levelno, Log.Level.DEBUG)
                ato_tb: str | None = None
                py_tb: str | None = None

                source_file = record.pathname if record.pathname else None
                source_line = record.lineno if record.lineno else None

                exc_value = record.exc_info[1] if record.exc_info else None
                if exc_value and isinstance(exc_value, _BaseBaseUserException):
                    message = get_exception_display_message(exc_value)
                    ato_tb = render_ato_traceback(exc_value)
                    if record.exc_info:
                        py_tb = json.dumps(_extract_traceback_frames(*record.exc_info))
                else:
                    message = record.getMessage()
                    if record.exc_info and record.exc_info[1]:
                        py_tb = json.dumps(_extract_traceback_frames(*record.exc_info))

                db_logger.log(
                    level,
                    message,
                    logger_name=record.name,
                    audience=Log.Audience.DEVELOPER,
                    source_file=source_file,
                    source_line=source_line,
                    ato_traceback=ato_tb,
                    python_traceback=py_tb,
                    objects=None,
                )
            except Exception:
                pass

    def _should_log_to_console(self, record: logging.LogRecord) -> bool:
        """
        Determine if a record should be logged to console.

        All logs go to the database unfiltered. Console filtering rules:
        - Only atopile/faebryk/test loggers (exclude watchdog, httpcore, etc.)
        - Only INFO level and above (DEBUG goes to database only)
        """
        # name = record.name

        # Filter by logger name
        # if name.startswith(("watchdog", "fsevents")):
        #     return False
        # if not _is_serving():
        #     if name.startswith("httpcore") or name.startswith("atopile.server"):
        #         return False
        #     if not (
        #         name.startswith("atopile")
        #         or name.startswith("faebryk")
        #         or name.startswith("test")
        #     ):
        #         return False

        # Console only shows INFO and above
        if record.levelno < logging.INFO:
            return False

        return True

    def emit(self, record: logging.LogRecord) -> None:

        # Get scope level for tree visualization prefix
        scope_level = _log_scope_level.get()
        scope_prefix = "·" * scope_level if scope_level > 0 else ""

        # Apply prefix to a copy for DB write (don't mutate original record.msg)
        if scope_prefix:
            original_msg = record.msg
            original_args = record.args
            # Format the message first, then prefix it
            formatted = record.getMessage()
            record.msg = f"{scope_prefix}{formatted}"
            record.args = None

        # Database receives all logs unfiltered
        self._write_to_db(record)

        # Restore original for proper exception handling below
        if scope_prefix:
            record.msg = original_msg  # pyright: ignore[reportPossiblyUnboundVariable]
            record.args = original_args  # pyright: ignore[reportPossiblyUnboundVariable]

        # Console is filtered (INFO+, atopile/faebryk only, etc.)
        if not self._should_log_to_console(record):
            return

        # Render
        tb = self._get_traceback(record)
        if self.formatter:
            record.message = record.getMessage()
            if hasattr(self.formatter, "usesTime") and self.formatter.usesTime():
                record.asctime = self.formatter.formatTime(
                    record, self.formatter.datefmt
                )
            message = self.formatter.formatMessage(record)
        else:
            message = record.getMessage()

        # Apply scope prefix to rendered message
        if scope_prefix:
            message = f"{scope_prefix}{message}"

        renderable = self.render(
            record=record,
            traceback=tb,
            message_renderable=self.render_message(record, message),
        )

        try:
            if record.levelno >= logging.ERROR and record.exc_info:
                error_console.print(renderable, crop=False, overflow="ignore")
            else:
                self.console.print(renderable, crop=False, overflow="ignore")
        except Exception:
            self.handleError(record)


# =============================================================================
# Query Helpers
# =============================================================================

LOGS_DEFAULT_COUNT = 500
LOGS_MAX_COUNT = 5000


def normalize_log_levels(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    allowed = {m.value for m in Log.Level}
    levels = []
    for e in value:
        if not isinstance(e, str) or (lvl := e.strip().upper()) not in allowed:
            return None
        levels.append(lvl)
    return levels


def normalize_log_audience(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    aud = value.strip().lower()
    return aud if aud in {m.value for m in Log.Audience} else None


def _strip_stream_id(entry: dict[str, Any]) -> dict[str, Any]:
    if "id" not in entry:
        return entry
    return {k: v for k, v in entry.items() if k != "id"}


def _fetch_logs(
    log_class: type,
    identifier: str,
    *,
    context_filter: str | None,
    log_levels: list[str] | None,
    audience: str | None,
    after_id: int,
    count: int,
    order: str,
    is_test: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    """Generic log fetcher for both build and test logs."""
    max_count = max(1, min(count, LOGS_MAX_COUNT))
    if is_test:
        return log_class.fetch_chunk(
            identifier,
            test_name=context_filter,
            levels=log_levels,
            audience=audience,
            after_id=after_id,
            count=max_count,
            order=order,
        )
    return log_class.fetch_chunk(
        identifier,
        stage=context_filter,
        levels=log_levels,
        audience=audience,
        after_id=after_id,
        count=max_count,
        order=order,
    )


def load_build_logs(
    *,
    build_id: str,
    stage: str | None,
    log_levels: list[str] | None,
    audience: str | None,
    count: int,
) -> list[dict[str, Any]]:
    from atopile.model.sqlite import Logs

    rows, _ = _fetch_logs(
        Logs, build_id,
        context_filter=stage, log_levels=log_levels, audience=audience,
        after_id=0, count=count, order="DESC",
    )
    return [_strip_stream_id(r) for r in rows]


def load_test_logs(
    *,
    test_run_id: str,
    test_name: str | None,
    log_levels: list[str] | None,
    audience: str | None,
    count: int,
) -> list[dict[str, Any]]:
    from atopile.model.sqlite import TestLogs

    rows, _ = _fetch_logs(
        TestLogs, test_run_id,
        context_filter=test_name, log_levels=log_levels, audience=audience,
        after_id=0, count=count, order="DESC", is_test=True,
    )
    return [_strip_stream_id(r) for r in rows]


def load_build_logs_stream(
    *,
    build_id: str,
    stage: str | None,
    log_levels: list[str] | None,
    audience: str | None,
    after_id: int,
    count: int,
) -> tuple[list[dict[str, Any]], int]:
    from atopile.model.sqlite import Logs

    return _fetch_logs(
        Logs, build_id,
        context_filter=stage, log_levels=log_levels, audience=audience,
        after_id=after_id, count=count, order="ASC",
    )


def load_test_logs_stream(
    *,
    test_run_id: str,
    test_name: str | None,
    log_levels: list[str] | None,
    audience: str | None,
    after_id: int,
    count: int,
) -> tuple[list[dict[str, Any]], int]:
    from atopile.model.sqlite import TestLogs

    return _fetch_logs(
        TestLogs, test_run_id,
        context_filter=test_name, log_levels=log_levels, audience=audience,
        after_id=after_id, count=count, order="ASC", is_test=True,
    )


# =============================================================================
# Module Init
# =============================================================================

handler = LogHandler(console=error_console)
handler.setFormatter(_DEFAULT_FORMATTER)
logging.basicConfig(level=logging.DEBUG, handlers=[handler])

if _is_serving():
    handler.console = console

atexit.register(BuildLogger.close_all)
atexit.register(LoggerForTest.close_all)

if PLOG:
    from faebryk.libs.picker.picker import logger as plog

    plog.setLevel(logging.DEBUG)

logger: AtoLogger = logging.getLogger(__name__)  # type: ignore[assignment]


def get_logger(name: str) -> AtoLogger:
    """Get typed AtoLogger instance."""
    return logging.getLogger(name)  # type: ignore[return-value]
