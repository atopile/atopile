"""
Logging infrastructure for atopile builds.

Provides SQLite-based structured logging, Rich console output, and audience
classification.
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType, TracebackType
from typing import Any

from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.text import Text
from rich.traceback import Traceback

import atopile
import faebryk
from atopile.dataclasses import (
    Log,
    LogRow,
    TestLogRow,
)
from atopile.errors import UserPythonModuleError, _BaseBaseUserException
from atopile.logging_utils import (
    LEVEL_CHAR,
    LEVEL_STYLES,
    PLOG,
    console,
    error_console,
)

# Suppress noisy third-party loggers
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("http11").setLevel(logging.INFO)

_DEFAULT_FORMATTER = logging.Formatter("%(message)s", datefmt="[%X]")
_log_scope_level: ContextVar[int] = ContextVar("log_scope_level", default=0)


@dataclass(frozen=True)
class _RecordMeta:
    """Per-log-call metadata that should be attached to each LogRecord."""

    audience: Log.Audience = Log.Audience.DEVELOPER
    objects: dict | None = None


_record_meta: ContextVar[_RecordMeta] = ContextVar(
    "record_meta",
    default=_RecordMeta(),
)

# Custom log level
ALERT = logging.INFO + 5
logging.addLevelName(ALERT, "ALERT")

# Level conversion lookup
_LEVEL_MAP = {
    logging.DEBUG: Log.Level.DEBUG,
    logging.INFO: Log.Level.INFO,
    ALERT: Log.Level.ALERT,
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
    """
    Unified logger: audience-aware methods + optional DB writing.

    Every logger in the codebase is an AtoLogger (via ``setLoggerClass``).
    Plain instances (from ``get_logger(__name__)``) only participate in the
    standard handler pipeline. Build and test contexts are explicit overrides;
    all other logs persist to an implicit unscoped context.
    """

    BATCH_SIZE = 300
    FLUSH_INTERVAL = 0.5

    _active_build_logger = None
    _active_test_logger = None
    _active_unscoped_logger = None
    _periodic_flush_thread: threading.Thread | None = None
    _periodic_flush_stop = threading.Event()

    @classmethod
    def _deactivate_logger(cls, logger: "AtoLogger | None") -> None:
        if logger is None:
            return
        logger.db_flush()
        logger._db_writer = None

    @classmethod
    def _set_active_loggers(
        cls,
        *,
        build: "AtoLogger | None" = None,
        test: "AtoLogger | None" = None,
        unscoped: "AtoLogger | None" = None,
    ) -> None:
        next_active = {
            id(logger) for logger in (build, test, unscoped) if logger is not None
        }
        for current in (
            cls._active_build_logger,
            cls._active_test_logger,
            cls._active_unscoped_logger,
        ):
            if current is not None and id(current) not in next_active:
                cls._deactivate_logger(current)

        cls._active_build_logger = build
        cls._active_test_logger = test
        cls._active_unscoped_logger = unscoped

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)
        # Ensure manually-instantiated AtoLogger still reaches root handlers.
        if self.parent is None:
            self.parent = logging.getLogger()
        # DB writer state (inactive by default)
        self._db_writer: Callable[[list[Any]], None] | None = None
        self._db_row_class: type | None = None
        self._db_id_field: str = ""
        self._db_context_field: str = ""
        self.stage_or_test_name: str = ""
        self._db_buffer: list[Any] = []
        self._db_buffer_lock = threading.Lock()
        self._db_identifier: str = ""

    # -----------------------------------------------------------------
    # Audience-aware logging overrides
    # -----------------------------------------------------------------

    @staticmethod
    @contextmanager
    def _with_record_meta(audience: Log.Audience, objects: dict | None):
        """
        Scope audience/objects for a single log call.

        The standard logging flow later calls makeRecord(), which reads this context
        and writes first-class LogRecord fields.
        """
        token = _record_meta.set(_RecordMeta(audience=audience, objects=objects))
        try:
            yield
        finally:
            _record_meta.reset(token)

    def _emit_with_meta(
        self,
        level: int,
        msg: object,
        args,
        *,
        audience: Log.Audience,
        objects: dict | None,
        **kwargs,
    ) -> None:
        """Emit a log message at `level` with explicit audience/object metadata."""
        kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 2
        with self._with_record_meta(audience, objects):
            self._log(level, msg, args, **kwargs)

    def makeRecord(  # type: ignore[override]
        self,
        name: str,
        level: int,
        fn: str,
        lno: int,
        msg: object,
        args,
        exc_info,
        func: str | None = None,
        extra: dict[str, Any] | None = None,
        sinfo=None,
    ) -> logging.LogRecord:
        """Create a LogRecord with first-class audience/objects fields."""
        record = logging._logRecordFactory(
            name,
            level,
            fn,
            lno,
            msg,
            args,
            exc_info,
            func,
            sinfo,
        )

        meta = _record_meta.get()
        record.__dict__["audience"] = meta.audience
        record.__dict__["objects"] = meta.objects

        if extra is not None:
            for key in extra:
                if (key in ["message", "asctime"]) or (key in record.__dict__):
                    raise KeyError(f"Attempt to overwrite {key!r} in LogRecord")
                record.__dict__[key] = extra[key]
        return record

    def debug(  # type: ignore[override]
        self,
        msg: object,
        *args,
        audience: Log.Audience = Log.Audience.DEVELOPER,
        objects: dict | None = None,
        **kwargs,
    ) -> None:
        if self.isEnabledFor(logging.DEBUG):
            self._emit_with_meta(
                logging.DEBUG,
                msg,
                args,
                audience=audience,
                objects=objects,
                **kwargs,
            )

    def info(  # type: ignore[override]
        self,
        msg: object,
        *args,
        audience: Log.Audience = Log.Audience.DEVELOPER,
        objects: dict | None = None,
        **kwargs,
    ) -> None:
        if self.isEnabledFor(logging.INFO):
            self._emit_with_meta(
                logging.INFO,
                msg,
                args,
                audience=audience,
                objects=objects,
                **kwargs,
            )

    def warning(  # type: ignore[override]
        self,
        msg: object,
        *args,
        audience: Log.Audience = Log.Audience.DEVELOPER,
        objects: dict | None = None,
        **kwargs,
    ) -> None:
        if self.isEnabledFor(logging.WARNING):
            self._emit_with_meta(
                logging.WARNING,
                msg,
                args,
                audience=audience,
                objects=objects,
                **kwargs,
            )

    def error(  # type: ignore[override]
        self,
        msg: object,
        *args,
        audience: Log.Audience = Log.Audience.DEVELOPER,
        objects: dict | None = None,
        **kwargs,
    ) -> None:
        if self.isEnabledFor(logging.ERROR):
            self._emit_with_meta(
                logging.ERROR,
                msg,
                args,
                audience=audience,
                objects=objects,
                **kwargs,
            )

    def alert(
        self,
        msg: object,
        *args,
        objects: dict | None = None,
        **kwargs,
    ) -> None:
        """Log at ALERT level (between WARNING and ERROR)."""
        if self.isEnabledFor(ALERT):
            self._emit_with_meta(
                ALERT,
                msg,
                args,
                audience=Log.Audience.USER,
                objects=objects,
                **kwargs,
            )

    # -----------------------------------------------------------------
    # DB writer plumbing
    # -----------------------------------------------------------------

    def set_writer(
        self,
        writer: Callable[[list[Any]], None],
        row_class: type,
        id_field: str,
        context_field: str,
    ) -> None:
        self._db_writer = writer
        self._db_row_class = row_class
        self._db_id_field = id_field
        self._db_context_field = context_field

    @property
    def build_id(self) -> str:
        return self._db_identifier

    def _write_db_entry(
        self,
        *,
        level: Log.Level,
        message: str,
        logger_name: str = "",
        audience: Log.Audience = Log.Audience.DEVELOPER,
        source_file: str | None = None,
        source_line: int | None = None,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
        objects: dict | None = None,
    ) -> None:
        """Build a DB entry, buffer it, and flush when batch threshold is met."""
        if self._db_writer is None or self._db_row_class is None:
            raise RuntimeError(
                f"DB logger '{self.name}' is not initialized or has been deactivated"
            )

        entry = self._db_row_class(
            **{
                self._db_id_field: self._db_identifier,
                self._db_context_field: self.stage_or_test_name,
                "timestamp": datetime.now().isoformat(),
                "level": level.value,
                "message": message,
                "logger_name": logger_name,
                "audience": audience.value,
                "source_file": source_file,
                "source_line": source_line,
                "ato_traceback": ato_traceback,
                "python_traceback": python_traceback,
                "objects": json.dumps(objects) if objects is not None else None,
            }
        )
        with self._db_buffer_lock:
            self._db_buffer.append(entry)
            should_flush = len(self._db_buffer) >= self.BATCH_SIZE
        if should_flush:
            self.db_flush()

    def db_flush(self) -> None:
        if self._db_writer is None:
            raise RuntimeError(
                f"DB logger '{self.name}' is not initialized or has been deactivated"
            )
        with self._db_buffer_lock:
            if not self._db_buffer:
                return
            entries, self._db_buffer = self._db_buffer, []
        self._db_writer(entries)

    # -----------------------------------------------------------------
    # Logging context activation
    # -----------------------------------------------------------------

    @classmethod
    def activate_build(cls, *, stage: str = "") -> "AtoLogger":
        env_build_id = os.environ["ATO_BUILD_ID"]

        from atopile.model.sqlite import Logs

        Logs.init_db()
        build_logger = cls._make_db_logger(
            env_build_id,
            stage,
            Logs.append_chunk,
            LogRow,
            "build_id",
            "stage",
            f"atopile.db.build.{env_build_id}",
        )
        cls._set_active_loggers(
            build=build_logger,
            unscoped=cls._get_or_create_unscoped_logger(),
        )
        return build_logger

    @classmethod
    def set_active_stage(cls, stage: str) -> None:
        """Set the current build stage on the active build logger context."""
        if cls._active_build_logger is None:
            raise RuntimeError("No active build logging context")
        cls._active_build_logger.stage_or_test_name = stage

    @classmethod
    def activate_test(cls, test_run_id: str, test: str = "") -> "AtoLogger":
        from atopile.model.sqlite import TestLogs

        TestLogs.init_db()
        TestLogs.register_run(test_run_id)

        test_logger = cls._make_db_logger(
            test_run_id,
            test,
            TestLogs.append_chunk,
            TestLogRow,
            "test_run_id",
            "test_name",
            f"atopile.db.test.{test_run_id}",
        )
        cls._set_active_loggers(
            test=test_logger,
            unscoped=cls._get_or_create_unscoped_logger(),
        )
        return test_logger

    @classmethod
    def set_active_test_name(cls, test: str) -> None:
        """Set the current test name on the active test logger context."""
        cls._active_test_logger.stage_or_test_name = test

    @staticmethod
    def get_build_log_db() -> Path:
        from faebryk.libs.paths import get_log_dir

        return get_log_dir() / "build_logs.db"

    @staticmethod
    def get_test_log_db() -> Path:
        from faebryk.libs.paths import get_log_dir

        return get_log_dir() / "test_logs.db"

    # -----------------------------------------------------------------
    # Shared class methods
    # -----------------------------------------------------------------

    @classmethod
    def close_all(cls) -> None:
        """Flush all active contexts, then close build/test while keeping unscoped."""
        cls.flush_all()
        cls._set_active_loggers(unscoped=cls._active_unscoped_logger)

    @classmethod
    def flush_all(cls) -> None:
        """Flush pending logs from currently active contexts without closing."""
        seen: set[int] = set()
        for logger in (
            cls._active_build_logger,
            cls._active_test_logger,
            cls._active_unscoped_logger,
        ):
            if logger is None or id(logger) in seen:
                continue
            seen.add(id(logger))
            logger.db_flush()

    @classmethod
    def start_periodic_flush(cls) -> None:
        """Start a background thread that periodically flushes active log buffers."""
        thread = cls._periodic_flush_thread
        if thread is not None and thread.is_alive():
            return

        cls._periodic_flush_stop.clear()

        def _periodic_flush_loop() -> None:
            while not cls._periodic_flush_stop.wait(timeout=cls.FLUSH_INTERVAL):
                cls.flush_all()

        cls._periodic_flush_thread = threading.Thread(
            target=_periodic_flush_loop,
            name="atopile-log-flusher",
            daemon=True,
        )
        cls._periodic_flush_thread.start()

    @classmethod
    def stop_periodic_flush(cls) -> None:
        """Stop the periodic flush thread."""
        cls._periodic_flush_stop.set()

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    @classmethod
    def _make_db_logger(
        cls,
        identifier: str,
        context: str,
        writer: Callable[[list[Any]], None],
        row_class: type,
        id_field: str,
        context_field: str,
        logger_name: str,
    ) -> "AtoLogger":
        """Create a lightweight AtoLogger wired for DB writing."""
        inst = logging.getLogger(logger_name)
        if not isinstance(inst, cls):
            inst = cls(logger_name)
            inst.parent = logging.getLogger()
        inst._db_identifier = identifier
        inst.stage_or_test_name = context
        inst._db_buffer = []
        inst.set_writer(writer, row_class, id_field, context_field)
        return inst

    @classmethod
    def _get_or_create_unscoped_logger(cls) -> "AtoLogger":
        if cls._active_unscoped_logger is not None:
            return cls._active_unscoped_logger

        from atopile.model.sqlite import Logs

        Logs.init_db()
        cls._active_unscoped_logger = cls._make_db_logger(
            "",
            "",
            Logs.append_chunk,
            LogRow,
            "build_id",
            "stage",
            "atopile.db.unscoped.default",
        )
        return cls._active_unscoped_logger

    @classmethod
    @contextmanager
    def test_context(
        cls,
        *,
        kind: str | None = None,
        identifier: str = "test",
        context: str = "",
        reset_root: bool = False,
    ):
        """Isolate logger globals for tests and optionally activate one context."""
        root = logging.getLogger()
        prev_handlers = list(root.handlers)
        prev_level = root.level
        prev_active_build = cls._active_build_logger
        prev_active_test = cls._active_test_logger
        prev_active_unscoped = cls._active_unscoped_logger

        if reset_root:
            root.handlers = []
            root.setLevel(logging.WARNING)

        cls._active_build_logger = None
        cls._active_test_logger = None
        cls._active_unscoped_logger = None

        if kind is not None:
            if kind not in {"build", "test", "unscoped"}:
                raise ValueError(f"Unsupported test logger kind: {kind}")

            if kind == "test":
                logger = cls._make_db_logger(
                    identifier,
                    context,
                    lambda _rows: None,
                    TestLogRow,
                    "test_run_id",
                    "test_name",
                    f"atopile.db.test.{kind}.{identifier}.{time.time_ns()}",
                )
                cls._set_active_loggers(test=logger)
            else:
                logger = cls._make_db_logger(
                    "" if kind == "unscoped" else identifier,
                    context,
                    lambda _rows: None,
                    LogRow,
                    "build_id",
                    "stage",
                    f"atopile.db.test.{kind}.{identifier}.{time.time_ns()}",
                )
                if kind == "build":
                    cls._set_active_loggers(build=logger)
                else:
                    cls._set_active_loggers(unscoped=logger)

        try:
            yield root
        finally:
            if reset_root:
                root.handlers = prev_handlers
                root.setLevel(prev_level)
            cls._active_build_logger = prev_active_build
            cls._active_test_logger = prev_active_test
            cls._active_unscoped_logger = prev_active_unscoped


logging.setLoggerClass(AtoLogger)


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


# =============================================================================
# Rich Log Handler
# =============================================================================


class ConsoleLogHandler(RichHandler):
    """Rich console handler with custom prefix formatting and traceback handling."""

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

    def render_message(
        self, record: logging.LogRecord, message: str
    ) -> ConsoleRenderable:
        # Exception with __rich_console__ renders itself
        if record.exc_info and (exc := record.exc_info[1]):
            if isinstance(exc, ConsoleRenderable) or hasattr(exc, "__rich_console__"):
                return exc  # type: ignore

        from datetime import datetime

        from rich.table import Table

        # Subprocess source identifier (short form)
        log_source = os.environ.get("ATO_LOG_SOURCE")
        source_id = os.environ.get("ATO_BUILD_ID", "")[:4] if log_source else ""

        # Prefix components: [id] time L logger_name
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        level_name = record.levelname
        level_char = LEVEL_CHAR.get(level_name, level_name[0])
        logger_name = record.name
        if len(logger_name) > 18:
            logger_name = "…" + logger_name[-17:]
        logger_name = f"{logger_name:<18}"

        if not self._is_terminal or _is_serving():
            prefix_parts: list[str] = []
            if source_id:
                prefix_parts.append(f"[{source_id}]")
            prefix_parts.append(timestamp)
            prefix_parts.append(level_char)
            prefix_parts.append(logger_name.strip())
            prefix = "  ".join(prefix_parts) + "  "
            output = Text.from_ansi(f"{prefix}{message}")
            output.no_wrap = True
            output.overflow = "ignore"
            return output

        level_color = LEVEL_STYLES.get(level_name, "white")

        prefix = Text()
        if source_id:
            prefix.append(f"[{source_id}]  ", style="dim")
        prefix.append(f"{timestamp}  ", style="dim")
        prefix.append(level_char, style=f"{level_color} bold")
        prefix.append(f"  {logger_name}  ", style="dim")

        # Render message body: handle ANSI passthrough, markdown, markup
        has_ansi = "\x1b[" in message or "\033[" in message
        if has_ansi:
            msg_renderable: ConsoleRenderable = Text.from_ansi(message)
        elif not self._is_terminal:
            msg_renderable = Text(message)
        elif getattr(record, "markdown", False):
            msg_renderable = Markdown(message)
        else:
            use_markup = getattr(record, "markup", self.markup)
            msg_text = Text.from_markup(message) if use_markup else Text(message)
            if hl := getattr(record, "highlighter", self.highlighter):
                msg_text = hl(msg_text)
            if kw := (self.keywords or self.KEYWORDS):
                msg_text.highlight_words(kw, "logging.keyword")
            msg_renderable = msg_text

        table = Table.grid(padding=0)
        table.add_column(no_wrap=True)
        table.add_column()
        table.add_row(prefix, msg_renderable)
        return table

    def emit(self, record: logging.LogRecord) -> None:
        # Scope prefix for tree visualization
        scope_level = _log_scope_level.get()
        scope_prefix = "·" * scope_level if scope_level > 0 else ""

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

        if scope_prefix:
            message = f"{scope_prefix}{message}"

        if _is_serving():
            # VSCode Output should be plain text to avoid forced wrapping.
            from rich.text import Text

            plain = Text.from_ansi(message.replace("\r", "")).plain
            target = (
                error_console.file
                if (record.levelno >= logging.ERROR and record.exc_info)
                else self.console.file
            )
            target.write(plain + "\n")
            target.flush()
            return

        renderable = self.render(
            record=record,
            traceback=tb,
            message_renderable=self.render_message(record, message),
        )

        if record.levelno >= logging.ERROR and record.exc_info:
            error_console.print(renderable, crop=False, overflow="ignore")
        else:
            self.console.print(renderable, crop=False, overflow="ignore")


class _DBLogFilter(logging.Filter):
    """Exclude noisy third-party loggers from DB storage."""

    _excluded_prefixes = ("httpcore", "httpx", "http11", "connection")

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name.startswith(self._excluded_prefixes):
            return record.levelno > logging.DEBUG
        return True


class DBLogHandler(logging.Handler):
    """Persist records into build/test override contexts or default unscoped."""

    @classmethod
    def _resolve_db_target(cls) -> AtoLogger:
        if AtoLogger._active_test_logger and AtoLogger._active_build_logger:
            raise RuntimeError(
                "Build and test DB logging contexts active simultaneously"
            )

        if AtoLogger._active_test_logger:
            return AtoLogger._active_test_logger

        if AtoLogger._active_build_logger:
            return AtoLogger._active_build_logger

        return AtoLogger._get_or_create_unscoped_logger()

    def handleError(self, record: logging.LogRecord) -> None:  # noqa: N802
        """Never swallow DB logging failures."""
        _exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_value is None:
            raise RuntimeError("DBLogHandler failed without an active exception")
        raise exc_value.with_traceback(exc_tb)

    def emit(self, record: logging.LogRecord) -> None:
        db_logger = self._resolve_db_target()

        from atopile.errors import (
            extract_traceback_frames,
            get_exception_display_message,
            render_ato_traceback,
        )

        level = _LEVEL_MAP[record.levelno]
        audience = getattr(record, "audience", Log.Audience.DEVELOPER)
        objects = getattr(record, "objects", None)
        ato_tb: str | None = None
        py_tb: str | None = None

        # Apply scope prefix for tree visualization
        scope_level = _log_scope_level.get()
        if scope_level > 0:
            prefix = "·" * scope_level
        else:
            prefix = ""

        exc_value = record.exc_info[1] if record.exc_info else None
        if exc_value and isinstance(exc_value, _BaseBaseUserException):
            message = get_exception_display_message(exc_value)
            ato_tb = render_ato_traceback(exc_value)
            if record.exc_info:
                py_tb = json.dumps(extract_traceback_frames(*record.exc_info))
        else:
            message = record.getMessage()
            if record.exc_info and record.exc_info[1]:
                py_tb = json.dumps(extract_traceback_frames(*record.exc_info))

        if prefix:
            message = f"{prefix}{message}"

        db_logger._write_db_entry(
            level=level,
            message=message,
            logger_name=record.name,
            audience=audience,
            source_file=record.pathname or None,
            source_line=record.lineno or None,
            ato_traceback=ato_tb,
            python_traceback=py_tb,
            objects=objects,
        )


# =============================================================================
# Module Init
# =============================================================================

handler = ConsoleLogHandler(console=error_console)
handler.setFormatter(_DEFAULT_FORMATTER)
handler.setLevel(logging.INFO)
_db_handler = DBLogHandler(level=logging.DEBUG)
_db_handler.addFilter(_DBLogFilter())
logging.basicConfig(level=logging.DEBUG, handlers=[handler, _db_handler])

if _is_serving():
    handler.console = console


def _shutdown_logging() -> None:
    AtoLogger.stop_periodic_flush()
    AtoLogger.close_all()


AtoLogger.start_periodic_flush()
atexit.register(_shutdown_logging)

if PLOG:
    from faebryk.libs.picker.picker import logger as plog

    plog.setLevel(logging.DEBUG)

logger: AtoLogger = logging.getLogger(__name__)  # type: ignore[assignment]


def get_logger(name: str) -> AtoLogger:
    """Get typed AtoLogger instance."""
    return logging.getLogger(name)  # type: ignore[return-value]
