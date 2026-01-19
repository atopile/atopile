"""
Logging infrastructure for atopile builds.

This module provides:
- SQLite-based structured logging with typed API
- Rich console output with progress bars
- Log capture for build stages
- Audience classification (user, developer, agent)
"""

from __future__ import annotations

import io
import json
import logging
import os
import pickle
import shutil
import sqlite3
import struct
import sys
import threading
import time
import traceback
from collections.abc import Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum, StrEnum
from pathlib import Path
from types import ModuleType, TracebackType
from typing import TYPE_CHECKING

import pathvalidate
from rich._null_file import NullFile
from rich.console import Console, ConsoleRenderable, RenderableType
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.padding import Padding
from rich.progress import (
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    RenderableColumn,
    SpinnerColumn,
    Task,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Column
from rich.text import Text
from rich.traceback import Traceback

import atopile
import faebryk
from atopile.cli import console
from atopile.errors import UserPythonModuleError, _BaseBaseUserException
from faebryk.libs.util import Advancable

if TYPE_CHECKING:
    pass

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Use parent's timestamp if running as parallel worker, otherwise generate new one
NOW = os.environ.get("ATO_BUILD_TIMESTAMP") or datetime.now().strftime(
    "%Y-%m-%d_%H-%M-%S"
)
_DEFAULT_FORMATTER = logging.Formatter("%(message)s", datefmt="[%X]")
_SHOW_LOG_FILE_PATH_THRESHOLD = 120


# displayed during LoggingStage
ALERT = logging.INFO + 5
logging.addLevelName(ALERT, "ALERT")


# =============================================================================
# SQLite Logging - Typed API for structured build logs
# =============================================================================

# Schema for the logs table
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    stage TEXT NOT NULL,
    level TEXT NOT NULL,
    level_no INTEGER NOT NULL,
    audience TEXT NOT NULL DEFAULT 'developer',
    message TEXT NOT NULL,
    ato_traceback TEXT,
    python_traceback TEXT
);

CREATE INDEX IF NOT EXISTS idx_logs_stage ON logs(stage);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level_no);
CREATE INDEX IF NOT EXISTS idx_logs_audience ON logs(audience);
"""


class Audience(StrEnum):
    """Who a log message is intended for."""

    USER = "user"  # End users (syntax errors, build failures)
    DEVELOPER = "developer"  # Design debugging (parameter resolution)
    AGENT = "agent"  # AI agents consuming logs programmatically


class Level(StrEnum):
    """Log severity levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LevelNo(IntEnum):
    """Numeric log levels for filtering."""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR


@dataclass
class LogEntry:
    """A structured log entry."""

    timestamp: str
    stage: str
    level: Level
    level_no: int
    message: str
    audience: Audience = Audience.DEVELOPER
    ato_traceback: str | None = None
    python_traceback: str | None = None


class SQLiteLogWriter:
    """Thread-safe SQLite log writer with WAL mode and batching."""

    BATCH_SIZE = 50
    FLUSH_INTERVAL = 1.0  # seconds

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._local = threading.local()
        self._buffer: list[LogEntry] = []
        self._buffer_lock = threading.Lock()
        self._last_flush = datetime.now()
        self._closed = False
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                timeout=30.0,
            )
            # Configure for concurrent access
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
            self._local.connection.execute("PRAGMA temp_store=MEMORY")
            self._local.connection.execute("PRAGMA busy_timeout=30000")
        return self._local.connection

    def _init_database(self) -> None:
        """Initialize the database schema."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_connection()
        conn.executescript(SCHEMA_SQL)
        conn.commit()

    def write(self, entry: LogEntry) -> None:
        """Write a log entry (batched for performance)."""
        if self._closed:
            return

        with self._buffer_lock:
            self._buffer.append(entry)
            should_flush = (
                len(self._buffer) >= self.BATCH_SIZE
                or (datetime.now() - self._last_flush).total_seconds()
                > self.FLUSH_INTERVAL
            )

        if should_flush:
            self.flush()

    def flush(self) -> None:
        """Force write all buffered entries."""
        with self._buffer_lock:
            if not self._buffer:
                return
            entries = self._buffer.copy()
            self._buffer.clear()
            self._last_flush = datetime.now()

        if not entries:
            return

        conn = self._get_connection()
        try:
            conn.executemany(
                """
                INSERT INTO logs (
                    timestamp, stage, level, level_no, audience,
                    message, ato_traceback, python_traceback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.timestamp,
                        e.stage,
                        e.level,
                        e.level_no,
                        e.audience,
                        e.message,
                        e.ato_traceback,
                        e.python_traceback,
                    )
                    for e in entries
                ],
            )
            conn.commit()
        except sqlite3.Error:
            # On error, try to reconnect and retry once
            self._local.connection = None
            try:
                conn = self._get_connection()
                conn.executemany(
                    """
                    INSERT INTO logs (
                        timestamp, stage, level, level_no, audience,
                        message, ato_traceback, python_traceback
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            e.timestamp,
                            e.stage,
                            e.level,
                            e.level_no,
                            e.audience,
                            e.message,
                            e.ato_traceback,
                            e.python_traceback,
                        )
                        for e in entries
                    ],
                )
                conn.commit()
            except sqlite3.Error:
                pass  # Best effort - don't crash the build for logging failures

    def close(self) -> None:
        """Close the writer and flush pending entries."""
        self._closed = True
        self.flush()
        if hasattr(self._local, "connection") and self._local.connection is not None:
            try:
                self._local.connection.close()
            except sqlite3.Error:
                pass
            self._local.connection = None


class BuildLogger:
    """Typed logging interface for structured build logs."""

    def __init__(self, stage: str = ""):
        self._stage = stage
        self._writer: SQLiteLogWriter | None = None
        self._db_path: Path | None = None

    def set_stage(self, stage: str) -> None:
        """Update the current build stage."""
        self._stage = stage

    def set_writer(self, writer: SQLiteLogWriter) -> None:
        """Set the SQLite writer for this logger."""
        self._writer = writer

    def log(
        self,
        level: Level,
        message: str,
        *,
        audience: Audience = Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
    ) -> None:
        """
        Log a structured message to the build database.

        Args:
            level: Log severity level
            message: The log message
            audience: Who this message is intended for (default: DEVELOPER)
            ato_traceback: Optional ato source context for user exceptions
            python_traceback: Optional Python traceback string
        """
        if self._writer is None:
            return

        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            stage=self._stage,
            level=level,
            level_no=LevelNo[level.name].value,
            message=message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
        )
        self._writer.write(entry)

    def debug(
        self,
        message: str,
        *,
        audience: Audience = Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
    ) -> None:
        """Log a DEBUG level message."""
        self.log(
            Level.DEBUG,
            message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
        )

    def info(
        self,
        message: str,
        *,
        audience: Audience = Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
    ) -> None:
        """Log an INFO level message."""
        self.log(
            Level.INFO,
            message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
        )

    def warning(
        self,
        message: str,
        *,
        audience: Audience = Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
    ) -> None:
        """Log a WARNING level message."""
        self.log(
            Level.WARNING,
            message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
        )

    def error(
        self,
        message: str,
        *,
        audience: Audience = Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
    ) -> None:
        """Log an ERROR level message."""
        self.log(
            Level.ERROR,
            message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
        )

    def exception(
        self,
        exc: BaseException,
        *,
        audience: Audience = Audience.DEVELOPER,
        level: Level = Level.ERROR,
    ) -> None:
        """
        Log an exception with automatic traceback extraction.

        Args:
            exc: The exception to log
            audience: Who this message is intended for (default: DEVELOPER)
            level: Log level (defaults to ERROR)
        """
        # Get message from exception
        message = str(exc) or type(exc).__name__

        # Extract ato traceback for user exceptions
        ato_tb = None
        if hasattr(exc, "__rich_console__"):
            ato_tb = self._extract_ato_traceback(exc)

        # Get Python traceback
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

    def _extract_ato_traceback(self, exc: BaseException) -> str | None:
        """
        Extract the ato-specific traceback info (source location, code context).

        This renders the exception using Rich to a string buffer to capture
        the user-facing context like source file paths and code snippets.
        """
        try:
            from io import StringIO

            from rich.console import Console as RichConsole

            buffer = StringIO()
            temp_console = RichConsole(
                file=buffer,
                width=120,
                force_terminal=True,
            )

            if hasattr(exc, "__rich_console__"):
                renderables = exc.__rich_console__(temp_console, temp_console.options)
                # Skip the first renderable (title) since we use it as message
                for renderable in list(renderables)[1:]:
                    temp_console.print(renderable)

            result = buffer.getvalue().strip()
            return result if result else None
        except Exception:
            return None

    def flush(self) -> None:
        """Flush any buffered log entries."""
        if self._writer is not None:
            self._writer.flush()


# Build-level logger registry
_build_loggers: dict[Path, BuildLogger] = {}
_build_writers: dict[Path, SQLiteLogWriter] = {}


def get_build_logger(log_dir: Path, stage: str = "") -> BuildLogger:
    """
    Get or create a build logger for a log directory.

    All stages in a build share the same SQLite database (build_logs.db).
    The stage name is updated when entering each stage.
    """
    db_path = log_dir / "build_logs.db"

    if log_dir not in _build_loggers:
        # Create the writer if it doesn't exist
        if db_path not in _build_writers:
            _build_writers[db_path] = SQLiteLogWriter(db_path)

        build_logger = BuildLogger(stage)
        build_logger.set_writer(_build_writers[db_path])
        build_logger._db_path = db_path
        _build_loggers[log_dir] = build_logger
    else:
        build_logger = _build_loggers[log_dir]
        build_logger.set_stage(stage)

    return build_logger


def close_build_logger(log_dir: Path) -> None:
    """Close and flush a build logger."""
    if log_dir in _build_loggers:
        build_logger = _build_loggers.pop(log_dir)
        if build_logger._db_path and build_logger._db_path in _build_writers:
            writer = _build_writers.pop(build_logger._db_path)
            writer.close()


def close_all_build_loggers() -> None:
    """Close all build loggers (typically called at end of build)."""
    for log_dir in list(_build_loggers.keys()):
        close_build_logger(log_dir)


class SQLiteLogHandler(logging.Handler):
    """
    A logging.Handler that bridges standard Python logging to SQLite.

    This handler captures logs from the standard logging framework and
    writes them to the SQLite database using the BuildLogger.
    """

    def __init__(
        self,
        build_logger: BuildLogger,
        level: int = logging.DEBUG,
    ):
        super().__init__(level)
        self._build_logger = build_logger
        self._logged_exceptions: set[tuple] = set()

        # Filter to atopile/faebryk logs only
        self.addFilter(
            lambda record: record.name.startswith("atopile")
            or record.name.startswith("faebryk")
        )

    def _get_hashable(self, record: logging.LogRecord) -> tuple | None:
        """Get hashable representation of exception to deduplicate."""
        if exc_info := getattr(record, "exc_info", None):
            _, exc_value, _ = exc_info
            if exc_value and isinstance(exc_value, _BaseBaseUserException):
                return exc_value.get_frozen()
        return None

    def _level_to_enum(self, levelno: int) -> Level:
        """Convert logging level number to Level enum."""
        if levelno >= logging.ERROR:
            return Level.ERROR
        elif levelno >= logging.WARNING:
            return Level.WARNING
        elif levelno >= logging.INFO:
            return Level.INFO
        return Level.DEBUG

    def emit(self, record: logging.LogRecord) -> None:
        """Write log record to SQLite via BuildLogger."""
        # Deduplicate exceptions
        hashable = self._get_hashable(record)
        if hashable and hashable in self._logged_exceptions:
            return

        try:
            level = self._level_to_enum(record.levelno)

            # Handle user exceptions specially
            exc_value = None
            if record.exc_info and record.exc_info[1] is not None:
                exc_value = record.exc_info[1]

            if exc_value and isinstance(exc_value, _BaseBaseUserException):
                # Use exception title as message
                message = exc_value.title or type(exc_value).__name__

                # Extract ato-specific context
                ato_tb = self._build_logger._extract_ato_traceback(exc_value)

                # Get Python traceback
                exc_type, exc_val, exc_tb = record.exc_info  # type: ignore[misc]
                python_tb = "".join(
                    traceback.format_exception(exc_type, exc_val, exc_tb)
                )

                self._build_logger.log(
                    level,
                    message,
                    audience=Audience.USER,  # User exceptions are for users
                    ato_traceback=ato_tb,
                    python_traceback=python_tb,
                )
            else:
                # Regular log message
                message = record.getMessage()

                # Add Python traceback if present
                python_tb = None
                if record.exc_info and record.exc_info[1] is not None:
                    exc_type, exc_val, exc_tb = record.exc_info
                    python_tb = "".join(
                        traceback.format_exception(exc_type, exc_val, exc_tb)
                    )

                self._build_logger.log(
                    level,
                    message,
                    python_traceback=python_tb,
                )

            if hashable:
                self._logged_exceptions.add(hashable)

        except Exception:
            self.handleError(record)

    def close(self) -> None:
        """Flush the build logger on close."""
        self._build_logger.flush()
        super().close()


# =============================================================================
# Build Status and Events
# =============================================================================


class Status(str, Enum):
    """Build status states."""

    QUEUED = "queued"
    BUILDING = "building"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"


@dataclass
class ProjectState:
    """Aggregate state for a project containing multiple builds."""

    builds: list = field(default_factory=list)
    status: Status = Status.QUEUED
    completed: int = 0
    failed: int = 0
    warnings: int = 0
    building: int = 0
    queued: int = 0
    total: int = 0
    current_build: str | None = None
    current_stage: str | None = None
    elapsed: float = 0.0
    log_dir: Path | None = None


@dataclass(frozen=True)
class StageStatusEvent:
    name: str
    description: str
    progress: int
    total: int | None


@dataclass(frozen=True)
class StageCompleteEvent:
    duration: float
    status: str
    infos: int
    warnings: int
    errors: int
    alerts: int
    log_name: str
    description: str


def _emit_event(fd: int, event: StageStatusEvent | StageCompleteEvent) -> None:
    payload = pickle.dumps(event, protocol=pickle.HIGHEST_PROTOCOL)
    header = struct.pack(">I", len(payload))
    data = header + payload
    offset = 0
    while offset < len(data):
        offset += os.write(fd, data[offset:])


# =============================================================================
# Rich Console Logging Handlers
# =============================================================================


class LogHandler(RichHandler):
    """
    A logging handler that renders output with Rich.

    Suppresses frames from tracebacks conditionally depending on the exception type.
    """

    def __init__(
        self,
        *args,
        console: Console,
        rich_tracebacks: bool = True,
        show_path: bool = False,
        tracebacks_suppress: Iterable[str] | None = ["typer"],
        tracebacks_suppress_map: dict[type[BaseException], Iterable[ModuleType]]
        | None = {UserPythonModuleError: [atopile, faebryk]},
        tracebacks_unwrap: list[type[BaseException]] | None = [UserPythonModuleError],
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
            **kwargs,
        )
        self.tracebacks_suppress = tracebacks_suppress or []
        self.tracebacks_suppress_map = tracebacks_suppress_map or {}
        self.tracebacks_unwrap = tracebacks_unwrap or []
        if hide_traceback_types is None:
            from atopile.compiler import DslRichException

            hide_traceback_types = (_BaseBaseUserException, DslRichException)
        self.hide_traceback_types = hide_traceback_types
        self.always_show_traceback_types = always_show_traceback_types
        self.traceback_level = traceback_level
        self._logged_exceptions = set()
        self._is_terminal = force_terminal or console.is_terminal

        self.addFilter(
            lambda record: record.name.startswith("atopile")
            or record.name.startswith("faebryk")
        )

    def _get_suppress(
        self, exc_type: type[BaseException] | None
    ) -> Iterable[str | ModuleType]:
        """
        Get extended list of modules to suppress from tracebacks.
        """
        suppress: set[str | ModuleType] = set(self.tracebacks_suppress)
        if exc_type is not None:
            for _type in self.tracebacks_suppress_map:
                if issubclass(exc_type, _type) or isinstance(exc_type, _type):
                    suppress.update(self.tracebacks_suppress_map[_type])
        return list(suppress)

    def _unwrap_chained_exceptions(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> tuple[type[BaseException] | None, BaseException | None, TracebackType | None]:
        def unwrap(exc: BaseException, exc_type: type[BaseException]) -> BaseException:
            """
            Unwraps an exception chain until we reach an exception
            that is not an instance of _type.
            """
            while isinstance(exc, exc_type) and exc.__cause__ is not None:
                exc = exc.__cause__
            return exc

        if exc_type is not None and exc_value is not None:
            while any(issubclass(exc_type, _type) for _type in self.tracebacks_unwrap):
                exc_value = unwrap(exc_value, exc_type)
                exc_type = type(exc_value)
                exc_traceback = exc_value.__traceback__

        return exc_type, exc_value, exc_traceback

    def _get_traceback(self, record: logging.LogRecord) -> Traceback | None:
        if not record.exc_info:
            return None

        exc_type, exc_value, exc_traceback = record.exc_info

        suppress = self._get_suppress(exc_type)

        hide_traceback = (
            isinstance(exc_value, self.hide_traceback_types)
            and not isinstance(exc_value, self.always_show_traceback_types)
        ) or record.levelno < self.traceback_level

        if isinstance(exc_value, UserPythonModuleError):
            exc_type, exc_value, exc_traceback = self._unwrap_chained_exceptions(
                exc_type, exc_value, exc_traceback
            )

        if hide_traceback or exc_type is None or exc_value is None:
            return None

        return Traceback.from_exception(
            exc_type,
            exc_value,
            exc_traceback,
            width=self.tracebacks_width,
            extra_lines=self.tracebacks_extra_lines,
            theme=self.tracebacks_theme,
            word_wrap=self.tracebacks_word_wrap,
            show_locals=self.tracebacks_show_locals,
            locals_max_length=self.locals_max_length,
            locals_max_string=self.locals_max_string,
            suppress=suppress,
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
        if not self._is_terminal:
            return Text(message)

        use_markdown = getattr(record, "markdown", False)
        use_markup = getattr(record, "markup", self.markup)
        highlighter = getattr(record, "highlighter", self.highlighter)

        if use_markdown:
            message_text = Markdown(message)
        else:
            message_text = Text.from_markup(message) if use_markup else Text(message)

            if highlighter:
                message_text = highlighter(message_text)

            if self.keywords is None:
                self.keywords = self.KEYWORDS

            if self.keywords:
                message_text.highlight_words(self.keywords, "logging.keyword")

        return message_text

    def render_message(
        self, record: logging.LogRecord, message: str
    ) -> ConsoleRenderable:
        if record.exc_info is not None:
            exc = record.exc_info[1]
            if isinstance(exc, ConsoleRenderable) or hasattr(exc, "__rich_console__"):
                # Rich-renderable exceptions include source chunks
                return exc  # type: ignore[return-value]

        return self._render_message(record, message)

    def _get_hashable(self, record: logging.LogRecord) -> tuple | None:
        if exc_info := getattr(record, "exc_info", None):
            _, exc_value, _ = exc_info
            if exc_value and isinstance(exc_value, _BaseBaseUserException):
                return exc_value.get_frozen()
        return None

    def _prepare_emit(self, record: logging.LogRecord) -> ConsoleRenderable:
        traceback_obj = self._get_traceback(record)

        if self.formatter:
            record.message = record.getMessage()
            formatter = self.formatter
            if hasattr(formatter, "usesTime") and formatter.usesTime():
                record.asctime = formatter.formatTime(record, formatter.datefmt)
            message = formatter.formatMessage(record)
        else:
            message = record.getMessage()

        message_renderable = self.render_message(record, message)

        log_renderable = self.render(
            record=record, traceback=traceback_obj, message_renderable=message_renderable
        )

        return log_renderable

    def emit(self, record: logging.LogRecord) -> None:
        """Invoked by logging."""
        # Worker subprocesses suppress console output, except for errors
        is_worker = bool(os.environ.get("ATO_BUILD_EVENT_FD"))
        is_console = self.console.file in (sys.stdout, sys.stderr)
        if is_worker and is_console and record.levelno < logging.ERROR:
            return

        hashable = self._get_hashable(record)
        if hashable and hashable in self._logged_exceptions:
            return None

        log_renderable = self._prepare_emit(record)

        if isinstance(self.console.file, NullFile):
            # Handles pythonw, where stdout/stderr are null, and we return NullFile
            # instance from Console.file. In this case, we still want to make a log
            # record even though we won't be writing anything to a file.
            self.handleError(record)
        else:
            try:
                self.console.print(log_renderable)
            except Exception:
                self.handleError(record)
            finally:
                if hashable:
                    self._logged_exceptions.add(hashable)


class LiveLogHandler(LogHandler):
    def __init__(self, status: "LoggingStage", *args, **kwargs):
        super().__init__(*args, console=status._console, **kwargs)
        self.status = status
        # In worker mode, we only count warnings/errors but don't print to console
        self._suppress_output = status._in_worker_mode

    def emit(self, record: logging.LogRecord) -> None:
        hashable = self._get_hashable(record)
        if hashable and hashable in self._logged_exceptions:
            return

        try:
            if record.levelno >= logging.ERROR:
                self.status._error_count += 1
            elif record.levelno >= logging.WARNING:
                self.status._warning_count += 1
            elif record.levelno == ALERT:
                self.status._alert_count += 1
            elif record.levelno >= logging.INFO:
                self.status._info_count += 1

            self.status.refresh()

            # In worker mode, only print errors to console
            if self._suppress_output:
                if record.levelno >= logging.ERROR:
                    super().emit(record)
                return

            if record.levelno == ALERT:
                self.status.alert(record.getMessage())
            elif record.levelno >= logging.ERROR:
                super().emit(record)

        except Exception:
            self.handleError(record)
        finally:
            if hashable:
                self._logged_exceptions.add(hashable)


class CaptureLogHandler(LogHandler):
    def __init__(self, status: "LoggingStage", console: Console, *args, **kwargs):
        super().__init__(*args, console=console, **kwargs)
        self.status = status

    def emit(self, record: logging.LogRecord) -> None:
        hashable = self._get_hashable(record)
        if hashable and hashable in self._logged_exceptions:
            return

        try:
            super().emit(record)
        except Exception:
            self.handleError(record)
        finally:
            if hashable:
                self._logged_exceptions.add(hashable)


# =============================================================================
# Progress Bar Components
# =============================================================================


class IndentedProgress(Progress):
    def __init__(self, *args, indent: int = 20, **kwargs):
        self.indent = indent
        super().__init__(*args, **kwargs)

    def get_renderable(self):
        return Padding(super().get_renderable(), pad=(0, 0, 0, self.indent))


class ShortTimeElapsedColumn(TimeElapsedColumn):
    """Renders time elapsed."""

    def render(self, task: "Task") -> Text:
        """Show time elapsed."""
        elapsed = task.elapsed or 0
        return Text.from_markup(f"[blue][{elapsed:.1f}s][/blue]")


class StyledMofNCompleteColumn(MofNCompleteColumn):
    def render(self, task: "Task") -> Text:
        return Text.from_markup(
            f"[dim]{task.completed}[/dim]{self.separator}[dim]{task.total}[/dim]"
        )


class SpacerColumn(RenderableColumn):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, renderable=Text(), table_column=Column(ratio=1), **kwargs
        )


class CompletableSpinnerColumn(SpinnerColumn):
    class Status(StrEnum):
        SUCCESS = "[green]✓[/green]"
        FAILURE = "[red]✗[/red]"
        WARNING = "[yellow]⚠[/yellow]"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = None

    def complete(self, status: Status) -> None:
        self.status = status

    def render(self, task: "Task") -> RenderableType:
        text = (
            Text.from_markup(self.status)
            if self.status is not None
            else self.spinner.render(task.get_time())
        )
        return text


# =============================================================================
# Context Variables and Handler Registry
# =============================================================================

_log_sink_var = ContextVar[io.StringIO | None]("log_sink", default=None)

# Build-level SQLite log handler registry - shared across all stages in a build
# Key: log_dir path, Value: SQLiteLogHandler
_build_sqlite_handlers: dict[Path, SQLiteLogHandler] = {}


def get_or_create_sqlite_log_handler(log_dir: Path, stage: str) -> SQLiteLogHandler:
    """
    Get or create a shared SQLite log handler for a build.

    All stages in a build share the same SQLite database (build_logs.db).
    The stage name is updated when entering each stage.
    """
    if log_dir not in _build_sqlite_handlers:
        build_logger = get_build_logger(log_dir, stage)
        handler = SQLiteLogHandler(build_logger, level=logging.DEBUG)
        _build_sqlite_handlers[log_dir] = handler
    else:
        handler = _build_sqlite_handlers[log_dir]
        handler._build_logger.set_stage(stage)
    return handler


def close_sqlite_log_handler(log_dir: Path) -> None:
    """Close and remove the SQLite log handler for a log directory."""
    if log_dir in _build_sqlite_handlers:
        handler = _build_sqlite_handlers.pop(log_dir)
        handler.close()
    close_build_logger(log_dir)


@contextmanager
def capture_logs():
    log_sink = _log_sink_var.get()
    _log_sink_var.set(io.StringIO())
    _log_sink = _log_sink_var.get()
    assert _log_sink is not None
    yield _log_sink
    _log_sink_var.set(log_sink)


@contextmanager
def log_exceptions(log_sink: io.StringIO):
    from atopile.cli.excepthook import _handle_exception

    exc_log_console = Console(file=log_sink)
    exc_log_handler = LogHandler(console=exc_log_console)
    logger.addHandler(exc_log_handler)

    try:
        yield
    except Exception as e:
        _handle_exception(type(e), e, e.__traceback__)
        raise e
    finally:
        logger.removeHandler(exc_log_handler)


# =============================================================================
# LoggingStage - Build stage context manager
# =============================================================================


class LoggingStage(Advancable):
    # Timing file name constant
    TIMING_FILE = "stage_timings.json"

    def __init__(
        self, name: str, description: str, steps: int | None = None, indent: int = 20
    ):
        self.name = name
        self.description = description
        self.indent = indent
        self.steps = steps
        self._console = console.error_console
        self._info_count = 0
        self._warning_count = 0
        self._error_count = 0
        self._alert_count = 0
        self._info_log_path = None
        self._log_handler = None
        self._capture_log_handler = None
        self._file_handlers: list = []
        self._original_handlers: dict = {}
        self._sanitized_name = pathvalidate.sanitize_filename(self.name)
        self._result = None
        self._log_dir: Path | None = None
        self._stage_start_time: float = 0.0
        self._original_level = logging.INFO
        self._shared_file_handler = False

        # Worker subprocesses are identified by IPC env vars set by the parent.
        self._in_worker_mode = bool(os.environ.get("ATO_BUILD_EVENT_FD"))

        # Only create progress bar for non-worker (single-process) runs
        if not self._in_worker_mode:
            self._progress: IndentedProgress | None = IndentedProgress(
                *self._get_columns(),
                console=self._console,
                transient=False,
                auto_refresh=True,
                refresh_per_second=10,
                indent=self.indent,
                expand=True,
            )
        else:
            self._progress = None

    def _get_columns(self) -> tuple[ProgressColumn, ...]:
        show_log_file_path = (
            self._info_log_path and self._console.width >= _SHOW_LOG_FILE_PATH_THRESHOLD
        )

        indicator_col = CompletableSpinnerColumn()
        self._indicator_col = indicator_col

        return tuple(
            col
            for col in (
                indicator_col,
                TextColumn("{task.description}"),
                StyledMofNCompleteColumn() if self.steps is not None else None,
                ShortTimeElapsedColumn(),
                SpacerColumn(),
                TextColumn(
                    f"[dim]{self._info_log_path}[/dim]" if show_log_file_path else "",
                    justify="right",
                    table_column=Column(justify="right", overflow="ellipsis"),
                ),
            )
            if col is not None
        )

    def _update_columns(self) -> None:
        if self._progress is not None:
            self._progress.columns = self._get_columns()

    def alert(self, message: str) -> None:
        # In worker mode, alerts are suppressed (logged to file only)
        if self._in_worker_mode:
            return

        message = f"[bold][yellow]![/yellow] {message}[/bold]"

        self._console.print(
            Padding(Text.from_markup(message), pad=(0, 0, 0, self.indent)),
            highlight=True,
        )

    def _generate_description(self) -> str:
        problems = []
        if self._error_count > 0:
            plural_e = "s" if self._error_count > 1 else ""
            problems.append(f"[red]{self._error_count} error{plural_e}[/red]")

        if self._warning_count > 0:
            plural_w = "s" if self._warning_count > 1 else ""
            problems.append(f"[yellow]{self._warning_count} warning{plural_w}[/yellow]")

        problems_text = f" ({', '.join(problems)})" if problems else ""
        return f"{self.description}{problems_text}"

    def refresh(self) -> None:
        if self._in_worker_mode:
            return  # No progress bar to refresh

        if not hasattr(self, "_task_id"):
            return

        if self._progress is not None:
            self._progress.update(
                self._task_id, description=self._generate_description()
            )

    def set_total(self, total: int | None) -> None:
        self.steps = total
        self._current_progress = 0

        # Write progress to IPC if in worker mode
        self._emit_status_event()

        if self._in_worker_mode:
            # In worker mode, don't update progress bar
            return

        self._update_columns()
        if self._progress is not None:
            self._progress.update(self._task_id, total=total)
        self.refresh()

    def advance(self, advance: int = 1) -> None:
        self._current_progress = getattr(self, "_current_progress", 0) + advance

        # Write progress to IPC if in worker mode
        self._emit_status_event()

        if self._in_worker_mode:
            return  # Progress tracking handled differently
        assert self.steps is not None
        if self._progress is not None:
            self._progress.advance(self._task_id, advance)

    def _emit_status_event(self) -> None:
        """Emit current stage and progress over IPC."""
        event_fd = os.environ.get("ATO_BUILD_EVENT_FD")
        if not event_fd:
            return

        try:
            fd = int(event_fd)
        except ValueError:
            return

        try:
            progress = getattr(self, "_current_progress", 0)
            total = self.steps
            _emit_event(
                fd,
                StageStatusEvent(
                    name=self.name,
                    description=self.description,
                    progress=progress,
                    total=total,
                ),
            )
        except Exception:
            pass  # Don't fail if we can't write status

    def __enter__(self) -> "LoggingStage":
        self._setup_logging()
        self._current_progress = 0
        self._stage_start_time = time.time()

        # Write status to IPC if in worker mode (subprocess parallelism)
        self._emit_status_event()

        if self._in_worker_mode:
            # Worker mode: no progress bar, just track internally
            pass  # Start time already set above
        else:
            self._update_columns()
            if self._progress is not None:
                self._progress.start()
                self._task_id = self._progress.add_task(
                    self.description, total=self.steps if self.steps is not None else 1
                )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        elapsed = time.time() - getattr(self, "_stage_start_time", time.time())
        if exc_type is not None:
            try:
                from faebryk.libs.exceptions import iter_leaf_exceptions

                if isinstance(exc_val, BaseExceptionGroup):
                    for leaf in iter_leaf_exceptions(exc_val):
                        if isinstance(leaf, _BaseBaseUserException):
                            msg = leaf.message
                        else:
                            msg = str(leaf)
                        # Pass exc_info so LogHandler can render rich source chunks
                        logger.error(
                            msg or "Build step failed",
                            exc_info=(type(leaf), leaf, leaf.__traceback__),
                        )
                else:
                    if isinstance(exc_val, _BaseBaseUserException):
                        msg = exc_val.message
                    else:
                        msg = str(exc_val)
                    logger.error(
                        msg or "Build step failed",
                        exc_info=(type(exc_val), exc_val, exc_val.__traceback__),
                    )
            except Exception:
                msg = str(exc_val) if exc_val is not None else "Build step failed"
                logger.error(
                    msg or "Build step failed",
                    exc_info=(type(exc_val), exc_val, exc_val.__traceback__)
                    if exc_val is not None
                    else None,
                )

        if exc_type is not None or self._error_count > 0:
            status = CompletableSpinnerColumn.Status.FAILURE
        elif self._warning_count > 0:
            status = CompletableSpinnerColumn.Status.WARNING
        else:
            status = CompletableSpinnerColumn.Status.SUCCESS

        self._restore_logging()
        self._emit_stage_event(elapsed, status)

        if self._in_worker_mode:
            # Worker mode: no display updates (handled by parent process)
            pass
        else:
            # Normal mode: update progress bar
            if self._progress is not None:
                for column in self._progress.columns:
                    if isinstance(column, CompletableSpinnerColumn):
                        column.complete(status)

                self.refresh()
                self._progress.stop()

    def _emit_stage_event(
        self, elapsed: float, status: CompletableSpinnerColumn.Status
    ) -> None:
        """
        Emit stage completion event to pipe for parent process.

        The parent process reads these events to build stage history,
        which is later written to JSON at build completion.
        """
        event_fd = os.environ.get("ATO_BUILD_EVENT_FD")
        if not event_fd:
            return
        try:
            fd = int(event_fd)
        except ValueError:
            return
        try:
            if status == CompletableSpinnerColumn.Status.FAILURE:
                status_text = "failed"
            elif status == CompletableSpinnerColumn.Status.WARNING:
                status_text = "warning"
            else:
                status_text = "success"
            _emit_event(
                fd,
                StageCompleteEvent(
                    duration=elapsed,
                    status=status_text,
                    infos=self._info_count,
                    warnings=self._warning_count,
                    errors=self._error_count,
                    alerts=self._alert_count,
                    log_name=self.name,
                    description=self.description,
                ),
            )
        except Exception:
            pass

    def _create_log_dir(self) -> Path:
        from atopile.config import config

        base_log_dir = Path(config.project.paths.logs) / "archive" / NOW

        try:
            build_cfg = config.build
            log_dir = base_log_dir / pathvalidate.sanitize_filename(build_cfg.name)
        except RuntimeError:
            log_dir = base_log_dir

        log_dir.mkdir(parents=True, exist_ok=True)

        # Store log directory for parallel display
        self._log_dir = log_dir

        # Skip symlink update in worker mode - it's handled by the summary generator
        if self._in_worker_mode:
            return log_dir

        # Update the latest symlink (single-threaded mode only)
        latest_link = Path(config.project.paths.logs) / "latest"
        try:
            if latest_link.is_symlink():
                latest_link.unlink()
            elif latest_link.exists():
                shutil.rmtree(latest_link)
            latest_link.symlink_to(base_log_dir, target_is_directory=True)
        except OSError:
            # If we can't symlink, just don't symlink
            # Logs are still written to the dated directory
            # Seems to happen on Windows if 'Developer Mode' is not enabled
            pass

        return log_dir

    def _setup_logging(self) -> None:
        root_logger = logging.getLogger()

        self._original_level = root_logger.level
        self._original_handlers = {"root": root_logger.handlers.copy()}

        # log all messages to at least one handler
        root_logger.setLevel(logging.DEBUG)

        self._log_handler = LiveLogHandler(self)
        self._log_handler.setFormatter(_DEFAULT_FORMATTER)
        self._log_handler.setLevel(self._original_level)

        if _log_sink_var.get() is not None:
            capture_console = Console(file=_log_sink_var.get())
            self._capture_log_handler = CaptureLogHandler(self, console=capture_console)
            self._capture_log_handler.setFormatter(_DEFAULT_FORMATTER)
            self._capture_log_handler.setLevel(logging.INFO)

        log_dir = self._create_log_dir()

        for handler in root_logger.handlers.copy():
            root_logger.removeHandler(handler)

        root_logger.addHandler(self._log_handler)
        if self._capture_log_handler is not None:
            root_logger.addHandler(self._capture_log_handler)

        self._file_handlers = []

        # Use shared SQLite log database (build_logs.db) with stage field
        # All stages in a build write to the same database
        sqlite_handler = get_or_create_sqlite_log_handler(log_dir, self.name)
        self._file_handlers.append(sqlite_handler)
        self._shared_file_handler = True  # Mark as shared, don't close on restore
        root_logger.addHandler(sqlite_handler)

        log_file = log_dir / "build_logs.db"
        try:
            self._info_log_path = log_file.relative_to(Path.cwd())
        except ValueError:
            self._info_log_path = log_file

    def _restore_logging(self) -> None:
        if not self._log_handler and not self._file_handlers:
            return

        root_logger = logging.getLogger()
        root_logger.setLevel(self._original_level)

        if self._log_handler in root_logger.handlers:
            root_logger.removeHandler(self._log_handler)

        if self._capture_log_handler in root_logger.handlers:
            root_logger.removeHandler(self._capture_log_handler)

        for file_handler in self._file_handlers:
            if file_handler in root_logger.handlers:
                root_logger.removeHandler(file_handler)
                # Don't close shared handlers - they persist across stages
                if not getattr(self, "_shared_file_handler", False):
                    file_handler.close()

        for handler in root_logger.handlers.copy():
            root_logger.removeHandler(handler)

        for handler in self._original_handlers.get("root", []):
            root_logger.addHandler(handler)

        self._original_handlers = {}
        self._original_level = logging.INFO
        self._log_handler = None
        self._capture_log_handler = None
        self._file_handlers = []
        self._shared_file_handler = False


# =============================================================================
# Faebryk Logging Utilities (formerly faebryk.libs.logging)
# =============================================================================

import re

import rich
from rich.highlighter import RegexHighlighter
from rich.table import Table
from rich.tree import Tree

from faebryk.libs.util import ConfigFlag, ConfigFlagInt


def rich_print_robust(message: str, markdown: bool = False):
    """
    Hack for terminals that don't support unicode
    There is probably a better way to do this, but this is a quick fix for now.
    """
    try:
        rich.print(Markdown(message) if markdown else message)
    except UnicodeEncodeError:
        message = message.encode("ascii", errors="ignore").decode("ascii")
        rich.print(Markdown(message) if markdown else message)
    except Exception:
        # Handle errors from Pygments plugin loading (e.g., old entry points)
        # or other rendering issues - fall back to plain text
        if markdown:
            # Try to extract plain text from markdown code blocks
            # Remove markdown code block syntax but keep content
            plain_message = re.sub(r"```\w*\n", "", message)
            plain_message = re.sub(r"```$", "", plain_message, flags=re.MULTILINE)
            rich.print(plain_message)
        else:
            rich.print(message)


def is_piped_to_file() -> bool:
    return not sys.stdout.isatty()


def get_terminal_width() -> int:
    if is_piped_to_file():
        if "COLUMNS" in os.environ:
            return int(os.environ["COLUMNS"])
        else:
            return 240
    else:
        return Console().size.width


PLOG = ConfigFlag("PLOG", descr="Enable picker debug log")
FLOG_FMT = ConfigFlag("LOG_FMT", descr="Enable (old) log formatting")
TERMINAL_WIDTH = ConfigFlagInt(
    "TERMINAL_WIDTH",
    default=get_terminal_width(),
    descr="Width of the terminal",
)


LOG_TIME = ConfigFlag("LOG_TIME", default=True, descr="Enable logging of time")
LOG_FILEINFO = ConfigFlag(
    "LOG_FILEINFO", default=True, descr="Enable logging of file info"
)

TIME_LEN = 5 + 2 if LOG_TIME else 0
LEVEL_LEN = 1
FILE_LEN = 12 + 4 if LOG_FILEINFO else 0
FMT_HEADER_LEN = TIME_LEN + 1 + LEVEL_LEN + 1 + FILE_LEN + 1

NET_LINE_WIDTH = min(120, int(TERMINAL_WIDTH) - FMT_HEADER_LEN)


class NestedConsole(Console):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            record=True,
            width=NET_LINE_WIDTH - 1,
            file=io.StringIO(),
            force_terminal=True,  # Enable ANSI colors for frontend rendering
            **kwargs,
        )

    def __str__(self):
        return self.export_text(styles=True)


def rich_to_string(rich_obj: Table | Tree) -> str:
    nested_console = NestedConsole()
    nested_console.print(rich_obj)
    return str(nested_console)


# Abbreviated level names with Rich color markup
_LEVEL_ABBREV = {
    "DEBUG": "[cyan]D[/cyan]",
    "INFO": "[green]I[/green]",
    "WARNING": "[yellow]W[/yellow]",
    "ERROR": "[red]E[/red]",
    "CRITICAL": "[bold red]C[/bold red]",
}


def format_line(line: str) -> str:
    # doesn't take ansii codes like `\x1b[0m\` into account that don't take space
    stripped_line = line.lstrip(" ")
    prefix = " " * ((len(line) - len(stripped_line)) + 2)
    chunk_size = NET_LINE_WIDTH - len(prefix)
    stripped_line = stripped_line.rstrip()
    lines = []
    for i in range(0, len(stripped_line), chunk_size):
        chunk = stripped_line[i : i + chunk_size]
        lines.append(f"{prefix}{chunk}")

    return "\n".join(lines).removeprefix(" " * 2)


class RelativeTimeFormatter(logging.Formatter):
    """Custom formatter with ms-since-start timestamp and abbreviated colored levels."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.perf_counter()

    def format(self, record: logging.LogRecord) -> str:
        # Calculate ms since logging started
        elapsed_s = time.perf_counter() - self.start_time
        record.elapsed_ms = f"{elapsed_s:>3.2f}s".rjust(7)

        # Replace level name with abbreviated colored version
        record.level_abbrev = _LEVEL_ABBREV.get(record.levelname, record.levelname)

        INDENT = " " * (FMT_HEADER_LEN + 1)
        message = record.getMessage()
        message = message.replace("\n", f"\n{INDENT}")
        if "\x1b" not in message:
            # If any line is longer than NET_LINE_WIDTH, wrap into chunks.
            if NET_LINE_WIDTH > 0 and len(message) > NET_LINE_WIDTH:
                message = "\n".join(format_line(line) for line in message.splitlines())

        record.nmessage = message

        # fileinfo
        filename, ext = record.filename.rsplit(".", 1)
        if len(filename) > 12:
            filename = filename[:5] + "..." + filename[-4:]
        lineno = record.lineno
        fileinfo = f"{filename}:{lineno}"
        record.fileinfo = f"{fileinfo:16s}"

        return super().format(record)


class NodeHighlighter(RegexHighlighter):
    """
    Apply style to anything that looks like an faebryk fabll.Node\n
    <*|XOR_with_NANDS.nands[2]|NAND.inputs[0]|Logic> with
      <*|TI_CD4011BE.nands[2]|ElectricNAND.inputs[0]|ElectricLogic>\n
    \t<> = fabll.Node\n
    \t|  = Type\n
    \t.  = Parent\n
    \t*  = Root
    """

    base_style = "node."
    highlights = [
        #  r"(?P<Rest>(.*))",
        r"(?P<Node>([/</>]))",
        r"[?=\|](?P<Type>([a-zA-Z_0-9]+))[?=\>]",
        r"[\.](?P<Child>([a-zA-Z_0-9]+))[?=\[]",
        r"[\|](?P<Parent>([a-zA-Z_0-9]+))[?=\.]",
        r"[?<=*.](?P<Root>(\*))",
        r"[?=\[](?P<Number>([0-9]+))[?=\]]",
        # Solver/Parameter stuff -------------------------------------------------------
        # Literals
        r"(?P<Quantity>Quantity_Interval(_Disjoint)?\([^)]*\))",
        r"(?P<Quantity>\(\[[^)]*\]\))",
        r"(?P<Quantity>\[(True|False)+\])",
        # Predicates / Expressions
        r"(?P<Op> (\+|\*|/))[ {]",
        r"(?P<Predicate> (is|⊆|≥|≤|)!?!?[✓✗]?) ",
        # Literal Is/IsSubset
        r"(?P<IsSubset>{(I|S)\|[^}]+})",
    ]


class ReprHighlighter(RegexHighlighter):
    """Highlights the text typically produced from ``__repr__`` methods."""

    base_style = "repr."
    highlights = [
        r"(?P<tag_start><)(?P<tag_name>[-\w.:|]*)(?P<tag_contents>[\w\W]*)(?P<tag_end>>)",
        r'(?P<attrib_name>[\w_]{1,50})=(?P<attrib_value>"?[\w_]+"?)?',
        r"(?P<brace>[][{}()])",
        "|".join(
            [
                r"(?P<ipv4>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
                r"(?P<ipv6>([A-Fa-f0-9]{1,4}::?){1,7}[A-Fa-f0-9]{1,4})",
                r"(?P<eui64>(?:[0-9A-Fa-f]{1,2}-){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){3}[0-9A-Fa-f]{4})",
                r"(?P<eui48>(?:[0-9A-Fa-f]{1,2}-){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})",
                r"(?P<call>[\w.]*?)\(",
                r"\b(?P<bool_true>True)\b|\b(?P<bool_false>False)\b|\b(?P<none>None)\b",
                r"(?P<ellipsis>\.\.\.)",
                r"(?P<number_complex>(?<!\w)(?:\-?[0-9]+\.?[0-9]*(?:e[-+]?\d+?)?)(?:[-+](?:[0-9]+\.?[0-9]*(?:e[-+]?\d+)?))?j)",
                r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b|0x[0-9a-fA-F]*)",
                # matches paths with or without leading / (@windows)
                r"(?P<path>(\b|/)([-\w._+]+)(/[-\w._+]+)*/)(?P<filename>[-\w._+]*)?",
                r"(?<![\\\w])(?P<str>b?'''.*?(?<!\\)'''|b?'.*?(?<!\\)'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
                r"(?P<url>(file|https|http|ws|wss)://[-0-9a-zA-Z$_+!`(),.?/;:&=%#~@]*)",
            ]
        ),
    ]


def setup_basic_logging():
    if FLOG_FMT:
        flog_handler = RichHandler(
            console=Console(
                safe_box=False,
                theme=console.faebryk_theme,
                force_terminal=True,
                width=int(TERMINAL_WIDTH),
            ),
            highlighter=NodeHighlighter(),
            show_path=False,  # Disable path column, we include it in format
            show_level=False,  # Disable level column, we include it in format
            show_time=False,  # Disable time column, we include it in format
            markup=True,  # Enable Rich markup in format string
        )
        flog_handler.setFormatter(
            RelativeTimeFormatter(
                ("[dim]%(fileinfo)s[/dim] " if LOG_FILEINFO else "")
                + ("[dim]%(elapsed_ms)s[/dim] " if LOG_TIME else "")
                + "%(level_abbrev)s %(nmessage)s"
            )
        )
        # force=True clears existing handlers so our formatter is used
        logging.basicConfig(level=logging.INFO, handlers=[flog_handler], force=True)

    if PLOG:
        from faebryk.libs.picker.picker import logger as plog

        plog.setLevel(logging.DEBUG)

    logging.getLogger("httpx").setLevel(logging.WARNING)


# =============================================================================
# Module-level initialization
# =============================================================================

handler = LogHandler(console=console.error_console)
handler.setFormatter(_DEFAULT_FORMATTER)

if FLOG_FMT:
    setup_basic_logging()
else:
    logging.basicConfig(level=logging.INFO, handlers=[handler])

logger = logging.getLogger(__name__)
