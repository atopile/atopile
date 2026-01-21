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
import re
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
from enum import Enum, StrEnum
from pathlib import Path
from types import ModuleType, TracebackType
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

import pathvalidate
import rich
from rich._null_file import NullFile
from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.padding import Padding
from rich.progress import ProgressColumn, TextColumn
from rich.table import Column, Table
from rich.tree import Tree
from rich.text import Text
from rich.traceback import Traceback

import atopile
import faebryk
from atopile.errors import UserPythonModuleError, _BaseBaseUserException
from atopile.logging_utils import (
    PLOG,
    CompletableSpinnerColumn,
    IndentedProgress,
    NestedConsole,
    ShortTimeElapsedColumn,
    SpacerColumn,
    StyledMofNCompleteColumn,
    error_console,
    format_line,
)
from faebryk.libs.util import Advancable

# =============================================================================
# Rich Console Configuration (formerly cli/console.py)
# =============================================================================
# (Imported from logging_utils at top of file)

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
-- Builds table: maps project/target/instance to a unique build_id
CREATE TABLE IF NOT EXISTS builds (
    build_id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    target TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_builds_project ON builds(project_path);
CREATE INDEX IF NOT EXISTS idx_builds_timestamp ON builds(timestamp);

-- Logs table: all log entries from all builds
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    stage TEXT NOT NULL,
    level TEXT NOT NULL,
    audience TEXT NOT NULL DEFAULT 'developer',
    message TEXT NOT NULL,
    ato_traceback TEXT,
    python_traceback TEXT,
    objects TEXT,
    FOREIGN KEY (build_id) REFERENCES builds(build_id)
);

CREATE INDEX IF NOT EXISTS idx_logs_build_id ON logs(build_id);
CREATE INDEX IF NOT EXISTS idx_logs_stage ON logs(stage);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_audience ON logs(audience);
"""

# Schema for the test logs table (different from build logs)
TEST_SCHEMA_SQL = """
-- Test runs table: maps test run to a unique test_run_id
CREATE TABLE IF NOT EXISTS test_runs (
    test_run_id TEXT PRIMARY KEY,
    run_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_test_runs_timestamp ON test_runs(timestamp);

-- Test logs table: all log entries from all test runs
CREATE TABLE IF NOT EXISTS test_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_run_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    test TEXT NOT NULL,
    level TEXT NOT NULL,
    audience TEXT NOT NULL DEFAULT 'developer',
    message TEXT NOT NULL,
    ato_traceback TEXT,
    python_traceback TEXT,
    objects TEXT,
    FOREIGN KEY (test_run_id) REFERENCES test_runs(test_run_id)
);

CREATE INDEX IF NOT EXISTS idx_test_logs_test_run_id ON test_logs(test_run_id);
CREATE INDEX IF NOT EXISTS idx_test_logs_test ON test_logs(test);
CREATE INDEX IF NOT EXISTS idx_test_logs_level ON test_logs(level);
CREATE INDEX IF NOT EXISTS idx_test_logs_audience ON test_logs(audience);
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


EntryT = TypeVar("EntryT")


class LogWriter(Protocol[EntryT]):
    def write(self, entry: EntryT) -> None: ...

    def flush(self) -> None: ...


class BaseLogger(Generic[EntryT]):
    """Common structured logger base for build/test loggers."""

    def __init__(self, identifier: str, context: str = ""):
        self._identifier = identifier
        self._context = context
        self._writer: LogWriter[EntryT] | None = None

    @staticmethod
    def _atopile_log_filter(record: logging.LogRecord) -> bool:
        """Filter to only include atopile and faebryk logs."""
        return record.name.startswith("atopile") or record.name.startswith("faebryk")

    @staticmethod
    def get_exception_display_message(exc: BaseException) -> str:
        """
        Get a unified display message for any exception.

        For UserException types, returns the message attribute (the detailed description).
        Falls back to str(exc) for other exceptions.
        """
        if isinstance(exc, _BaseBaseUserException):
            # Use message for the detailed error description
            # message is the user-facing explanation of what went wrong
            return exc.message or str(exc) or type(exc).__name__
        return str(exc) or type(exc).__name__

    @staticmethod
    @contextmanager
    def capture_logs():
        log_sink = _log_sink_var.get()
        _log_sink_var.set(io.StringIO())
        _log_sink = _log_sink_var.get()
        assert _log_sink is not None
        yield _log_sink
        _log_sink_var.set(log_sink)

    @staticmethod
    @contextmanager
    def log_exceptions(log_sink: io.StringIO):
        from atopile.cli.excepthook import _handle_exception

        exc_log_console = Console(file=log_sink)
        exc_log_handler = LogHandler(console=exc_log_console)
        logger.addHandler(exc_log_handler)

        try:
            yield
        except Exception as exc:
            _handle_exception(type(exc), exc, exc.__traceback__)
            raise exc
        finally:
            logger.removeHandler(exc_log_handler)

    def set_context(self, context: str) -> None:
        """Update the current context label (stage/test name)."""
        self._context = context

    def set_writer(self, writer: LogWriter[EntryT]) -> None:
        """Set the SQLite writer for this logger."""
        self._writer = writer

    def log(
        self,
        level: Level,
        message: str,
        *,
        logger_name: str = "",
        audience: Audience = Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
        objects: dict | None = None,
    ) -> None:
        """Log a structured message to the database."""
        if self._writer is None:
            return

        entry = self._build_entry(
            level=level,
            message=message,
            logger_name=logger_name,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
            objects=objects,
        )
        self._writer.write(entry)

    def debug(
        self,
        message: str,
        *,
        audience: Audience = Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
        objects: dict | None = None,
    ) -> None:
        """Log a DEBUG level message."""
        self.log(
            Level.DEBUG,
            message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
            objects=objects,
        )

    def info(
        self,
        message: str,
        *,
        audience: Audience = Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
        objects: dict | None = None,
    ) -> None:
        """Log an INFO level message."""
        self.log(
            Level.INFO,
            message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
            objects=objects,
        )

    def warning(
        self,
        message: str,
        *,
        audience: Audience = Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
        objects: dict | None = None,
    ) -> None:
        """Log a WARNING level message."""
        self.log(
            Level.WARNING,
            message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
            objects=objects,
        )

    def error(
        self,
        message: str,
        *,
        audience: Audience = Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
        objects: dict | None = None,
    ) -> None:
        """Log an ERROR level message."""
        self.log(
            Level.ERROR,
            message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
            objects=objects,
        )

    def flush(self) -> None:
        """Flush any buffered log entries."""
        if self._writer is not None:
            self._writer.flush()

    @staticmethod
    def rich_print_robust(message: str, markdown: bool = False) -> None:
        """
        Print a message with Rich, falling back to ASCII and plain text on errors.
        """
        try:
            rich.print(Markdown(message) if markdown else message)
        except UnicodeEncodeError:
            message = message.encode("ascii", errors="ignore").decode("ascii")
            rich.print(Markdown(message) if markdown else message)
        except Exception:
            if markdown:
                plain_message = re.sub(r"```\w*\n", "", message)
                plain_message = re.sub(r"```$", "", plain_message, flags=re.MULTILINE)
                rich.print(plain_message)
            else:
                rich.print(message)

    @staticmethod
    def is_piped_to_file() -> bool:
        return not sys.stdout.isatty()

    @staticmethod
    def get_terminal_width() -> int:
        if BaseLogger.is_piped_to_file():
            if "COLUMNS" in os.environ:
                return int(os.environ["COLUMNS"])
            return 240
        return Console().size.width

    @staticmethod
    def rich_to_string(rich_obj: "Table | Tree") -> str:
        nested_console = NestedConsole()
        nested_console.print(rich_obj)
        return str(nested_console)

    @staticmethod
    def format_line(line: str) -> str:
        """Format a line with proper wrapping. Delegates to logging_utils.format_line."""
        return format_line(line)

    def _build_entry(
        self,
        *,
        level: Level,
        message: str,
        logger_name: str,
        audience: Audience,
        ato_traceback: str | None,
        python_traceback: str | None,
        objects: dict | None,
    ) -> EntryT:
        raise NotImplementedError


@dataclass
class LogEntry:
    """A structured log entry."""

    build_id: str
    timestamp: str
    stage: str
    level: Level
    message: str
    audience: Audience = Audience.DEVELOPER
    ato_traceback: str | None = None
    python_traceback: str | None = None
    objects: dict | None = None


@dataclass
class TestLogEntry:
    """A structured test log entry."""

    test_run_id: str
    timestamp: str
    test: str  # Name of the Python test being run
    level: Level
    message: str
    audience: Audience = Audience.DEVELOPER
    ato_traceback: str | None = None
    python_traceback: str | None = None
    objects: dict | None = None


class SQLiteLogWriter:
    """Thread-safe SQLite log writer with WAL mode and batching."""

    BATCH_SIZE = 50
    FLUSH_INTERVAL = 1.0  # seconds

    # Singleton instance for central database
    _instance: SQLiteLogWriter | None = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> SQLiteLogWriter:
        """Get the singleton instance of the central log writer."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(BuildLogger.get_log_db())
            return cls._instance

    @classmethod
    def close_instance(cls) -> None:
        """Close the singleton instance."""
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None

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

    def register_build(self, project_path: str, target: str, timestamp: str) -> str:
        """
        Register a new build and return its build_id.

        If a build with the same project/target/timestamp already exists,
        returns the existing build_id.
        """
        build_id = BuildLogger.generate_build_id(project_path, target, timestamp)
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO builds (build_id, project_path, target, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (build_id, project_path, target, timestamp),
            )
            conn.commit()
        except sqlite3.Error:
            pass  # Best effort
        return build_id

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

    def _serialize_objects(self, objects: dict | None) -> str | None:
        """Serialize objects dict to JSON string."""
        if objects is None:
            return None
        try:
            return json.dumps(objects)
        except (TypeError, ValueError):
            return None

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
                    build_id, timestamp, stage, level, audience,
                    message, ato_traceback, python_traceback, objects
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.build_id,
                        e.timestamp,
                        e.stage,
                        e.level,
                        e.audience,
                        e.message,
                        e.ato_traceback,
                        e.python_traceback,
                        self._serialize_objects(e.objects),
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
                        build_id, timestamp, stage, level, audience,
                        message, ato_traceback, python_traceback, objects
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            e.build_id,
                            e.timestamp,
                            e.stage,
                            e.level,
                            e.audience,
                            e.message,
                            e.ato_traceback,
                            e.python_traceback,
                            self._serialize_objects(e.objects),
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


class SQLiteTestLogWriter:
    """Thread-safe SQLite test log writer with WAL mode and batching."""

    BATCH_SIZE = 50
    FLUSH_INTERVAL = 1.0  # seconds

    # Singleton instance for test database
    _instance: SQLiteTestLogWriter | None = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> SQLiteTestLogWriter:
        """Get the singleton instance of the test log writer."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(TestLogger.get_log_db())
            return cls._instance

    @classmethod
    def close_instance(cls) -> None:
        """Close the singleton instance."""
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._local = threading.local()
        self._buffer: list[TestLogEntry] = []
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
        conn.executescript(TEST_SCHEMA_SQL)
        conn.commit()

    def register_test_run(self, run_name: str, timestamp: str) -> str:
        """
        Register a new test run and return its test_run_id.

        If a test run with the same name/timestamp already exists,
        returns the existing test_run_id.
        """
        test_run_id = TestLogger.generate_test_run_id(run_name, timestamp)
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO test_runs (test_run_id, run_name, timestamp)
                VALUES (?, ?, ?)
                """,
                (test_run_id, run_name, timestamp),
            )
            conn.commit()
        except sqlite3.Error:
            pass  # Best effort
        return test_run_id

    def write(self, entry: TestLogEntry) -> None:
        """Write a test log entry (batched for performance)."""
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

    def _serialize_objects(self, objects: dict | None) -> str | None:
        """Serialize objects dict to JSON string."""
        if objects is None:
            return None
        try:
            return json.dumps(objects)
        except (TypeError, ValueError):
            return None

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
                INSERT INTO test_logs (
                    test_run_id, timestamp, test, level, audience,
                    message, ato_traceback, python_traceback, objects
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.test_run_id,
                        e.timestamp,
                        e.test,
                        e.level,
                        e.audience,
                        e.message,
                        e.ato_traceback,
                        e.python_traceback,
                        self._serialize_objects(e.objects),
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
                    INSERT INTO test_logs (
                        test_run_id, timestamp, test, level, audience,
                        message, ato_traceback, python_traceback, objects
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            e.test_run_id,
                            e.timestamp,
                            e.test,
                            e.level,
                            e.audience,
                            e.message,
                            e.ato_traceback,
                            e.python_traceback,
                            self._serialize_objects(e.objects),
                        )
                        for e in entries
                    ],
                )
                conn.commit()
            except sqlite3.Error:
                pass  # Best effort - don't crash tests for logging failures

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


class TestLogger(BaseLogger[TestLogEntry]):
    """Typed logging interface for structured test logs."""

    _loggers: dict[str, "TestLogger"] = {}

    def __init__(self, test_run_id: str, test: str = ""):
        super().__init__(test_run_id, test)

    @staticmethod
    def get_log_db() -> Path:
        """Get the path to the test log database."""
        from faebryk.libs.paths import get_log_dir

        return get_log_dir() / "test_logs.db"

    @staticmethod
    def generate_test_run_id(run_name: str, timestamp: str) -> str:
        """Generate a unique test run ID from run name and timestamp."""
        import hashlib

        content = f"{run_name}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @classmethod
    def get(
        cls,
        run_name: str,
        timestamp: str | None = None,
        test: str = "",
    ) -> "TestLogger":
        """
        Get or create a test logger for a test run.

        All logs go to the test database at ~/.local/share/atopile/test_logs.db.
        Each test run is identified by a unique test_run_id generated from name+timestamp.
        """
        if timestamp is None:
            timestamp = NOW

        writer = SQLiteTestLogWriter.get_instance()
        test_run_id = writer.register_test_run(run_name, timestamp)

        if test_run_id not in cls._loggers:
            test_logger = cls(test_run_id, test)
            test_logger.set_writer(writer)
            cls._loggers[test_run_id] = test_logger
        else:
            test_logger = cls._loggers[test_run_id]
            test_logger.set_test(test)

        return test_logger

    @classmethod
    def close(cls, test_run_id: str) -> None:
        """Close and flush a test logger by its test run ID."""
        if test_run_id in cls._loggers:
            test_logger = cls._loggers.pop(test_run_id)
            test_logger.flush()

    @classmethod
    def close_all(cls) -> None:
        """
        Close all test loggers and the test SQLite writer.

        This should be called at the end of a test session to ensure
        all logs are flushed and resources are properly released.
        """
        for test_run_id in list(cls._loggers.keys()):
            cls.close(test_run_id)
        SQLiteTestLogWriter.close_instance()

    @classmethod
    def setup_logging(
        cls,
        run_name: str,
        test: str = "",
        timestamp: str | None = None,
    ) -> "TestLogger | None":
        """
        Set up logging for test workers.

        This sets up logging to write to the test_logs.db database instead of
        build_logs.db. The schema uses test_run_id and test columns instead of
        build_id and stage.
        """
        root_logger = logging.getLogger()

        try:
            test_logger = cls.get(run_name, timestamp, test=test)
            for handler in root_logger.handlers:
                if isinstance(handler, LogHandler):
                    handler._test_logger = test_logger
                    break
            return test_logger
        except Exception:
            return None

    @classmethod
    def update_test_name(cls, test: str | None) -> None:
        """
        Update the current test name for test database logging.

        This updates the test logger's test name so that subsequent log entries
        are tagged with the correct test name.
        """
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, LogHandler):
                test_logger = getattr(handler, "_test_logger", None)
                if test_logger is not None:
                    test_logger.set_test(test or "")
                    break

    def set_test(self, test: str) -> None:
        """Update the current test name."""
        self.set_context(test)

    @property
    def test_run_id(self) -> str:
        """Get the test run ID for this logger."""
        return self._identifier

    def _build_entry(
        self,
        *,
        level: Level,
        message: str,
        logger_name: str,
        audience: Audience,
        ato_traceback: str | None,
        python_traceback: str | None,
        objects: dict | None,
    ) -> TestLogEntry:
        return TestLogEntry(
            test_run_id=self._identifier,
            timestamp=datetime.now().isoformat(),
            test=self._context,
            level=level,
            message=message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
            objects=objects,
        )


class BuildLogger(BaseLogger[LogEntry]):
    """Typed logging interface for structured build logs."""

    _loggers: dict[str, "BuildLogger"] = {}

    def __init__(self, build_id: str, stage: str = ""):
        super().__init__(build_id, stage)

    @staticmethod
    def get_log_db() -> Path:
        """Get the path to the central log database."""
        from faebryk.libs.paths import get_log_dir

        return get_log_dir() / "build_logs.db"

    @staticmethod
    def generate_build_id(project_path: str, target: str, timestamp: str) -> str:
        """Generate a unique build ID from project, target, and timestamp."""
        import hashlib

        content = f"{project_path}:{target}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @staticmethod
    def _emit_event(
        fd: int, event: "StageStatusEvent | StageCompleteEvent"
    ) -> None:
        payload = pickle.dumps(event, protocol=pickle.HIGHEST_PROTOCOL)
        header = struct.pack(">I", len(payload))
        data = header + payload
        offset = 0
        while offset < len(data):
            offset += os.write(fd, data[offset:])

    @classmethod
    def get(
        cls,
        project_path: str,
        target: str,
        timestamp: str | None = None,
        stage: str = "",
    ) -> "BuildLogger":
        """
        Get or create a build logger for a project/target/timestamp combination.

        All logs go to the central database at ~/.local/share/atopile/build_logs.db.
        Each build is identified by a unique build_id generated from project+target+timestamp.
        """
        if timestamp is None:
            timestamp = NOW

        writer = SQLiteLogWriter.get_instance()
        build_id = writer.register_build(project_path, target, timestamp)

        if build_id not in cls._loggers:
            build_logger = cls(build_id, stage)
            build_logger.set_writer(writer)
            cls._loggers[build_id] = build_logger
        else:
            build_logger = cls._loggers[build_id]
            build_logger.set_stage(stage)

        return build_logger

    @classmethod
    def get_by_id(cls, build_id: str) -> "BuildLogger | None":
        """Get an existing build logger by its build ID."""
        return cls._loggers.get(build_id)

    @classmethod
    def close(cls, build_id: str) -> None:
        """Close and flush a build logger by its build ID."""
        if build_id in cls._loggers:
            build_logger = cls._loggers.pop(build_id)
            build_logger.flush()

    @classmethod
    def close_all(cls) -> None:
        """
        Close all build loggers and the central SQLite writer.

        This should be called at the end of a build session to ensure
        all logs are flushed and resources are properly released.
        """
        for build_id in list(cls._loggers.keys()):
            cls.close(build_id)
        SQLiteLogWriter.close_instance()

    @classmethod
    def setup_logging(
        cls,
        enable_database: bool = True,
        stage: str | None = None,
        use_live_handler: bool = False,
        status: "LoggingStage | None" = None,
    ) -> "BuildLogger | None":
        """
        Unified logging setup function.

        Sets up logging with optional database support. Can be used for:
        - CLI commands (enable_database=True, stage="cli")
        - Build stages (enable_database=True, stage="stage-name", use_live_handler=True)
        - Basic Rich-formatted logging (enable_database=False)
        """
        root_logger = logging.getLogger()

        build_logger = None
        if enable_database:
            try:
                from atopile.config import config

                try:
                    project_path = str(config.project.paths.root.resolve())
                    target = config.build.name if hasattr(config, "build") else "cli"
                except (RuntimeError, AttributeError):
                    project_path = "cli"
                    target = "default"

                stage_name = stage if stage is not None else "cli"
                build_logger = cls.get(project_path, target, stage=stage_name)

                for handler in root_logger.handlers:
                    if isinstance(handler, LogHandler):
                        handler._build_logger = build_logger
                        break
            except Exception:
                pass

        if use_live_handler and status is not None and build_logger is not None:
            for handler in root_logger.handlers.copy():
                root_logger.removeHandler(handler)

            live_handler = LiveLogHandler(status, build_logger=build_logger)
            live_handler.setFormatter(_DEFAULT_FORMATTER)
            live_handler.setLevel(root_logger.level)
            root_logger.addHandler(live_handler)

            if _log_sink_var.get() is not None:
                capture_console = Console(file=_log_sink_var.get())
                capture_handler = CaptureLogHandler(status, console=capture_console)
                capture_handler.setFormatter(_DEFAULT_FORMATTER)
                capture_handler.setLevel(logging.INFO)
                root_logger.addHandler(capture_handler)

        return build_logger

    @classmethod
    def update_stage(cls, stage: str | None) -> None:
        """
        Update the current stage for database logging.

        This updates the build logger's stage so that subsequent log entries
        are tagged with the correct stage name. Also logs that the stage has started.
        """
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, LogHandler) and handler._build_logger is not None:
                handler._build_logger.set_stage(stage or "")
                if stage:
                    logger = logging.getLogger(__name__)
                    logger.debug(f"Starting build stage: {stage}")
                break

    def set_stage(self, stage: str) -> None:
        """Update the current build stage."""
        self.set_context(stage)

    @property
    def build_id(self) -> str:
        """Get the build ID for this logger."""
        return self._identifier

    def _build_entry(
        self,
        *,
        level: Level,
        message: str,
        logger_name: str,
        audience: Audience,
        ato_traceback: str | None,
        python_traceback: str | None,
        objects: dict | None,
    ) -> LogEntry:
        return LogEntry(
            build_id=self._identifier,
            timestamp=datetime.now().isoformat(),
            stage=self._context,
            level=level,
            message=message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
            objects=objects,
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


# =============================================================================
# Rich Console Logging Handlers
# =============================================================================


class LogHandler(RichHandler):
    """
    A logging handler that renders output with Rich.

    Suppresses frames from tracebacks conditionally depending on the exception type.
    Optionally supports database logging via BuildLogger.
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
        build_logger: "BuildLogger | None" = None,
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
        self._build_logger = build_logger
        self._test_logger: TestLogger | None = None
        # Note: We don't add _atopile_log_filter here because we want all logs
        # to go to the database. The filter is applied manually in emit() for
        # console output only.

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
            record=record,
            traceback=traceback_obj,
            message_renderable=message_renderable,
        )

        return log_renderable

    def _level_to_enum(self, levelno: int) -> Level:
        """Convert logging level number to Level enum."""
        if levelno >= logging.ERROR:
            return Level.ERROR
        elif levelno >= logging.WARNING:
            return Level.WARNING
        elif levelno >= logging.INFO:
            return Level.INFO
        return Level.DEBUG

    def _write_to_sqlite(self, record: logging.LogRecord) -> None:
        """Write log record to SQLite via BuildLogger or TestLogger if available."""
        # Write to build logger if available
        if self._build_logger is not None:
            self._write_to_build_logger(record)

        # Write to test logger if available
        if self._test_logger is not None:
            self._write_to_test_logger(record)

    def _write_to_build_logger(self, record: logging.LogRecord) -> None:
        """Write log record to build database via BuildLogger."""
        if self._build_logger is None:
            return

        try:
            level = self._level_to_enum(record.levelno)

            # Handle user exceptions specially
            exc_value = None
            if record.exc_info and record.exc_info[1] is not None:
                exc_value = record.exc_info[1]

            if exc_value and isinstance(exc_value, _BaseBaseUserException):
                # Use unified message extraction
                message = BaseLogger.get_exception_display_message(exc_value)

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
                    audience=Audience.USER,
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
        except Exception:
            pass  # Don't fail if SQLite logging fails

    def _write_to_test_logger(self, record: logging.LogRecord) -> None:
        """Write log record to test database via TestLogger."""
        if self._test_logger is None:
            return

        try:
            level = self._level_to_enum(record.levelno)

            # Handle user exceptions specially
            exc_value = None
            if record.exc_info and record.exc_info[1] is not None:
                exc_value = record.exc_info[1]

            if exc_value and isinstance(exc_value, _BaseBaseUserException):
                # Use unified message extraction
                message = BaseLogger.get_exception_display_message(exc_value)

                # Get Python traceback
                exc_type, exc_val, exc_tb = record.exc_info  # type: ignore[misc]
                python_tb = "".join(
                    traceback.format_exception(exc_type, exc_val, exc_tb)
                )

                self._test_logger.log(
                    level,
                    message,
                    audience=Audience.USER,
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

                self._test_logger.log(
                    level,
                    message,
                    python_traceback=python_tb,
                )
        except Exception:
            pass  # Don't fail if SQLite logging fails

    def emit(self, record: logging.LogRecord) -> None:
        """Invoked by logging."""
        # Only process atopile/faebryk logs (applies to both database and console)
        if not BaseLogger._atopile_log_filter(record):
            return

        # Write to database
        self._write_to_sqlite(record)

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
    """
    Log handler for build stages with integrated SQLite logging.

    Handles:
    - Rich console output (via parent LogHandler)
    - Progress bar updates (warning/error counts)
    - SQLite database logging (via BuildLogger)
    """

    def __init__(
        self,
        status: "LoggingStage",
        build_logger: "BuildLogger | None" = None,
        *args,
        **kwargs,
    ):
        # Pass build_logger to parent so it can write to database
        super().__init__(
            *args, console=status._console, build_logger=build_logger, **kwargs
        )
        self.status = status
        # In worker mode, we only count warnings/errors but don't print to console
        self._suppress_output = status._in_worker_mode

    def emit(self, record: logging.LogRecord) -> None:
        hashable = self._get_hashable(record)
        if hashable and hashable in self._logged_exceptions:
            return

        try:
            # Update progress bar counts
            if record.levelno >= logging.ERROR:
                self.status._error_count += 1
            elif record.levelno >= logging.WARNING:
                self.status._warning_count += 1
            elif record.levelno == ALERT:
                self.status._alert_count += 1
            elif record.levelno >= logging.INFO:
                self.status._info_count += 1

            self.status.refresh()

            # Write to SQLite database (always, regardless of console suppression)
            # Base class handles this, but we call it explicitly here to ensure
            # it happens before console output suppression
            self._write_to_sqlite(record)

            # Console output handling
            if self._suppress_output:
                # In worker mode, only print errors to console
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
# (Imported from logging_utils at top of file)


# =============================================================================
# Context Variables
# =============================================================================

_log_sink_var = ContextVar[io.StringIO | None]("log_sink", default=None)


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
        self._console = error_console
        self._info_count = 0
        self._warning_count = 0
        self._error_count = 0
        self._alert_count = 0
        self._info_log_path = None
        self._log_handler = None
        self._capture_log_handler = None
        self._original_handlers: dict = {}
        self._sanitized_name = pathvalidate.sanitize_filename(self.name)
        self._result = None
        self._stage_start_time: float = 0.0
        self._original_level = logging.INFO

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
            BuildLogger._emit_event(
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
                from atopile.exceptions import iter_leaf_exceptions

                if isinstance(exc_val, BaseExceptionGroup):
                    for leaf in iter_leaf_exceptions(exc_val):
                        # Use unified message extraction
                        msg = BaseLogger.get_exception_display_message(leaf)
                        # Pass exc_info so LogHandler can render rich source chunks
                        logger.error(
                            msg or "Build step failed",
                            exc_info=(type(leaf), leaf, leaf.__traceback__),
                        )
                else:
                    # Use unified message extraction
                    msg = BaseLogger.get_exception_display_message(exc_val)
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
            BuildLogger._emit_event(
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

    def _setup_logging(self) -> None:
        root_logger = logging.getLogger()

        self._original_level = root_logger.level
        self._original_handlers = {"root": root_logger.handlers.copy()}

        # log all messages to at least one handler
        root_logger.setLevel(logging.DEBUG)

        # Use unified setup_logging function
        build_logger = BuildLogger.setup_logging(
            enable_database=True,
            stage=self.name,
            use_live_handler=True,
            status=self,
        )

        if build_logger:
            self._build_id = build_logger.build_id
            logger.debug(
                f"Logs build_id: {self._build_id} (stage={self.name}, ts={NOW})"
            )

        # Store handlers for cleanup
        self._log_handler = None
        self._capture_log_handler = None
        for handler in root_logger.handlers:
            if isinstance(handler, LiveLogHandler):
                self._log_handler = handler
            elif isinstance(handler, CaptureLogHandler):
                self._capture_log_handler = handler

        # Show central log database path for info
        log_file = BuildLogger.get_log_db()
        try:
            self._info_log_path = log_file.relative_to(Path.cwd())
        except ValueError:
            self._info_log_path = log_file

    def _restore_logging(self) -> None:
        if not self._log_handler:
            return

        root_logger = logging.getLogger()
        root_logger.setLevel(self._original_level)

        if self._log_handler in root_logger.handlers:
            root_logger.removeHandler(self._log_handler)

        if self._capture_log_handler in root_logger.handlers:
            root_logger.removeHandler(self._capture_log_handler)

        for handler in root_logger.handlers.copy():
            root_logger.removeHandler(handler)

        for handler in self._original_handlers.get("root", []):
            root_logger.addHandler(handler)

        self._original_handlers = {}
        self._original_level = logging.INFO
        self._log_handler = None
        self._capture_log_handler = None

# =============================================================================
# Module-level initialization
# =============================================================================

# Always use LogHandler which supports both Rich console output and database logging
# Root logger is set to DEBUG so all debug messages go to the database.
# Console output is filtered to only show atopile/faebryk logs (see emit()).
handler = LogHandler(console=error_console)
handler.setFormatter(_DEFAULT_FORMATTER)
logging.basicConfig(level=logging.DEBUG, handlers=[handler])

# Ensure logs flush on process exit.
import atexit

atexit.register(BuildLogger.close_all)
atexit.register(TestLogger.close_all)

# Set up picker debug logging if enabled
if PLOG:
    from faebryk.libs.picker.picker import logger as plog

    plog.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
