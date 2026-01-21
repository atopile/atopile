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
import traceback
from collections.abc import Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum
from pathlib import Path
from types import ModuleType, TracebackType
from typing import TYPE_CHECKING, Any

from rich._null_file import NullFile
from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.text import Text
from rich.traceback import Traceback

import atopile
import faebryk
from atopile.buildutil import generate_build_id
from atopile.errors import UserPythonModuleError, _BaseBaseUserException
from atopile.logging_utils import (
    PLOG,
    error_console,
)

# =============================================================================
# Context Variables
# =============================================================================

_log_sink_var = ContextVar[io.StringIO | None]("log_sink", default=None)

# =============================================================================
# Build Status and Events
# =============================================================================

from atopile.dataclasses import (
    BuildStatus,
    Log,
    ProjectState,
    StageCompleteEvent,
    StageStatusEvent,
)

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

# Custom log level for alerts
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
    logger_name TEXT NOT NULL DEFAULT '',
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
-- Test runs table
CREATE TABLE IF NOT EXISTS test_runs (
    test_run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Test logs table: all log entries from all test runs
CREATE TABLE IF NOT EXISTS test_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_run_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    test_name TEXT NOT NULL,
    level TEXT NOT NULL,
    logger_name TEXT NOT NULL DEFAULT '',
    audience TEXT NOT NULL DEFAULT 'developer',
    message TEXT NOT NULL,
    ato_traceback TEXT,
    python_traceback TEXT,
    objects TEXT,
    FOREIGN KEY (test_run_id) REFERENCES test_runs(test_run_id)
);

CREATE INDEX IF NOT EXISTS idx_test_logs_test_run_id ON test_logs(test_run_id);
CREATE INDEX IF NOT EXISTS idx_test_logs_test_name ON test_logs(test_name);
CREATE INDEX IF NOT EXISTS idx_test_logs_level ON test_logs(level);
CREATE INDEX IF NOT EXISTS idx_test_logs_audience ON test_logs(audience);
"""


# Log.Audience and Log.Level are imported from atopile.dataclasses


class BaseLogger:
    """Common structured logger base for build/test loggers."""

    def __init__(self, identifier: str, context: str = ""):
        self._identifier = identifier
        self._context = context
        self._writer: Any | None = None

    @staticmethod
    def _atopile_log_filter(record: logging.LogRecord) -> bool:
        """Filter to only include atopile and faebryk logs, excluding server/http logs unless running 'ato serve'."""
        # Check if we're running the server (either via 'ato serve' or 'python -m atopile.server')
        main_module = sys.modules.get("__main__")
        is_serving = (
            "serve" in sys.argv
            or "atopile.server" in sys.argv
            or (main_module is not None and main_module.__package__ == "atopile.server")
        )

        # When running server, allow ALL logs to console
        if is_serving:
            return True
        # Filter out httpcore logs unless running server
        if record.name.startswith("httpcore"):
            return False
        if not (record.name.startswith("atopile") or record.name.startswith("faebryk")):
            return False
        # Filter server logs from console unless running server
        if record.name.startswith("atopile.server"):
            return False
        return True

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

    def set_writer(self, writer: Any) -> None:
        """Set the SQLite writer for this logger."""
        self._writer = writer

    def log(
        self,
        level: Log.Level,
        message: str,
        *,
        logger_name: str = "",
        audience: Log.Audience = Log.Audience.DEVELOPER,
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
        audience: Log.Audience = Log.Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
        objects: dict | None = None,
    ) -> None:
        """Log a DEBUG level message."""
        self.log(
            Log.Level.DEBUG,
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
        audience: Log.Audience = Log.Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
        objects: dict | None = None,
    ) -> None:
        """Log an INFO level message."""
        self.log(
            Log.Level.INFO,
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
        audience: Log.Audience = Log.Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
        objects: dict | None = None,
    ) -> None:
        """Log a WARNING level message."""
        self.log(
            Log.Level.WARNING,
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
        audience: Log.Audience = Log.Audience.DEVELOPER,
        ato_traceback: str | None = None,
        python_traceback: str | None = None,
        objects: dict | None = None,
    ) -> None:
        """Log an ERROR level message."""
        self.log(
            Log.Level.ERROR,
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


    def _build_entry(
        self,
        *,
        level: Log.Level,
        message: str,
        logger_name: str,
        audience: Log.Audience,
        ato_traceback: str | None,
        python_traceback: str | None,
        objects: dict | None,
    ) -> Any:
        raise NotImplementedError


# Log.Entry and Log.TestEntry are imported from atopile.dataclasses


class SQLiteLogWriter:
    """Thread-safe SQLite log writer with WAL mode and batching."""

    BATCH_SIZE = 50
    FLUSH_INTERVAL = 1.0  # seconds

    # Singleton instances for different databases
    _build_instance: "SQLiteLogWriter | None" = None
    _test_instance: "SQLiteLogWriter | None" = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_build_instance(cls) -> "SQLiteLogWriter":
        """Get the singleton instance for build logs."""
        with cls._instance_lock:
            if cls._build_instance is None:
                cls._build_instance = cls(
                    BuildLogger.get_log_db(),
                    SCHEMA_SQL,
                    """
                    INSERT INTO logs (
                        build_id, timestamp, stage, level, logger_name, audience,
                        message, ato_traceback, python_traceback, objects
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    lambda e: (
                        e.build_id,
                        e.timestamp,
                        e.stage,
                        e.level,
                        e.logger_name,
                        e.audience,
                        e.message,
                        e.ato_traceback,
                        e.python_traceback,
                    ),
                )
            return cls._build_instance

    @classmethod
    def get_test_instance(cls) -> "SQLiteLogWriter":
        """Get the singleton instance for test logs."""
        with cls._instance_lock:
            if cls._test_instance is None:
                cls._test_instance = cls(
                    TestLogger.get_log_db(),
                    TEST_SCHEMA_SQL,
                    """
                    INSERT INTO test_logs (
                        test_run_id, timestamp, test_name, level, logger_name, audience,
                        message, ato_traceback, python_traceback, objects
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    lambda e: (
                        e.test_run_id,
                        e.timestamp,
                        e.test_name,
                        e.level,
                        e.logger_name,
                        e.audience,
                        e.message,
                        e.ato_traceback,
                        e.python_traceback,
                    ),
                )
            return cls._test_instance

    @classmethod
    def close_build_instance(cls) -> None:
        """Close the build log writer instance."""
        with cls._instance_lock:
            if cls._build_instance is not None:
                cls._build_instance.close()
                cls._build_instance = None

    @classmethod
    def close_test_instance(cls) -> None:
        """Close the test log writer instance."""
        with cls._instance_lock:
            if cls._test_instance is not None:
                cls._test_instance.close()
                cls._test_instance = None

    def __init__(
        self,
        db_path: Path,
        schema_sql: str,
        insert_sql: str,
        entry_to_tuple: Any,
    ):
        self._db_path = db_path
        self._schema_sql = schema_sql
        self._insert_sql = insert_sql
        self._entry_to_tuple = entry_to_tuple
        self._local = threading.local()
        self._buffer: list[Any] = []
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
        conn.executescript(self._schema_sql)
        conn.commit()

    def register_build(self, project_path: str, target: str, timestamp: str) -> str:
        """
        Register a new build and return its build_id.

        If a build with the same project/target/timestamp already exists,
        returns the existing build_id.
        """
        build_id = generate_build_id(project_path, target, timestamp)
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

    def register_test_run(self, test_run_id: str) -> None:
        """Register a test run in the database."""
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO test_runs (test_run_id) VALUES (?)",
                (test_run_id,),
            )
            conn.commit()
        except sqlite3.Error:
            pass  # Best effort

    def write(self, entry: Any) -> None:
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
                self._insert_sql,
                [
                    (*self._entry_to_tuple(e), self._serialize_objects(e.objects))
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
                    self._insert_sql,
                    [
                        (*self._entry_to_tuple(e), self._serialize_objects(e.objects))
                        for e in entries
                    ],
                )
                conn.commit()
            except sqlite3.Error:
                pass  # Best effort - don't crash for logging failures

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


class TestLogger(BaseLogger):
    """Typed logging interface for structured test logs."""

    def __init__(self, test_run_id: str, test: str = ""):
        super().__init__(test_run_id, test)

    @staticmethod
    def get_log_db() -> Path:
        """Get the path to the test log database."""
        from faebryk.libs.paths import get_log_dir

        return get_log_dir() / "test_logs.db"

    @classmethod
    def close_all(cls) -> None:
        """
        Close the test SQLite writer.

        This should be called at the end of a test session to ensure
        all logs are flushed and resources are properly released.
        """
        SQLiteLogWriter.close_test_instance()

    @classmethod
    def setup_logging(
        cls,
        test_run_id: str,
        test: str = "",
    ) -> "TestLogger | None":
        """
        Set up logging for test workers.

        This sets up logging to write to the test_logs.db database instead of
        build_logs.db. The schema uses test_run_id and test_name columns instead of
        build_id and stage.
        """
        root_logger = logging.getLogger()

        try:
            writer = SQLiteLogWriter.get_test_instance()
            writer.register_test_run(test_run_id)
            test_logger = cls(test_run_id, test)
            test_logger.set_writer(writer)
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
        level: Log.Level,
        message: str,
        logger_name: str,
        audience: Log.Audience,
        ato_traceback: str | None,
        python_traceback: str | None,
        objects: dict | None,
    ) -> Log.TestEntry:
        return Log.TestEntry(
            test_run_id=self._identifier,
            timestamp=datetime.now().isoformat(),
            test_name=self._context,
            level=level,
            logger_name=logger_name,
            message=message,
            audience=audience,
            ato_traceback=ato_traceback,
            python_traceback=python_traceback,
            objects=objects,
        )


class BuildLogger(BaseLogger):
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

        writer = SQLiteLogWriter.get_build_instance()
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
        SQLiteLogWriter.close_build_instance()

    @classmethod
    def setup_logging(
        cls,
        enable_database: bool = True,
        stage: str | None = None,
    ) -> "BuildLogger | None":
        """
        Unified logging setup function.

        Sets up logging with optional database support. Can be used for:
        - CLI commands (enable_database=True, stage="cli")
        - Build stages (enable_database=True, stage="stage-name")
        - Basic Rich-formatted logging (enable_database=False)

        Args:
            enable_database: Whether to set up database logging
            stage: Stage name for database logging (defaults to "cli")
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

                # Attach build_logger to existing handler
                for handler in root_logger.handlers:
                    if isinstance(handler, LogHandler):
                        handler._build_logger = build_logger
                        break
            except Exception:
                pass

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
        level: Log.Level,
        message: str,
        logger_name: str,
        audience: Log.Audience,
        ato_traceback: str | None,
        python_traceback: str | None,
        objects: dict | None,
    ) -> Log.Entry:
        return Log.Entry(
            build_id=self._identifier,
            timestamp=datetime.now().isoformat(),
            stage=self._context,
            level=level,
            logger_name=logger_name,
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
        audience: Log.Audience = Log.Audience.DEVELOPER,
        level: Log.Level = Log.Level.ERROR,
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
        # Note: _atopile_log_filter is applied in both _write_to_sqlite() and
        # emit() to filter logs for database and console output respectively.

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

        # Use console width or None (unlimited) for traceback width to prevent truncation
        width = getattr(self, 'tracebacks_width', None) or getattr(self.console, 'width', None)
        # If width is None, Rich will use full available width
        
        return Traceback.from_exception(
            exc_type,
            exc_value,
            exc_traceback,
            width=width,
            extra_lines=getattr(self, 'tracebacks_extra_lines', 3),
            theme=getattr(self, 'tracebacks_theme', None),
            word_wrap=getattr(self, 'tracebacks_word_wrap', True),
            show_locals=getattr(self, 'tracebacks_show_locals', False),
            locals_max_length=getattr(self, 'locals_max_length', 10),
            locals_max_string=getattr(self, 'locals_max_string', 80),
            max_frames=getattr(self, 'tracebacks_max_frames', 1000),  # Increased from default 100 to show full tracebacks
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

    def _level_to_enum(self, levelno: int) -> Log.Level:
        """Convert logging level number to Level enum."""
        if levelno >= logging.ERROR:
            return Log.Level.ERROR
        elif levelno >= logging.WARNING:
            return Log.Level.WARNING
        elif levelno >= logging.INFO:
            return Log.Level.INFO
        return Log.Level.DEBUG

    def _write_to_sqlite(self, record: logging.LogRecord) -> None:
        """Write log record to SQLite via BuildLogger or TestLogger if available."""
        # Check if we're running the server (either via 'ato serve' or 'python -m atopile.server')
        main_module = sys.modules.get("__main__")
        is_serving = (
            "serve" in sys.argv
            or "atopile.server" in sys.argv
            or (main_module is not None and main_module.__package__ == "atopile.server")
        )
        # Skip database writes when running server
        if is_serving:
            return
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
                    logger_name=record.name,
                    audience=Log.Audience.USER,
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
                    logger_name=record.name,
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
                    logger_name=record.name,
                    audience=Log.Audience.USER,
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
                    logger_name=record.name,
                    python_traceback=python_tb,
                )
        except Exception:
            pass  # Don't fail if SQLite logging fails

    def emit(self, record: logging.LogRecord) -> None:
        """Invoked by logging."""
        # Filter out non-atopile/faebryk logs and httpcore (unless serving)
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
                # For errors/exceptions, also print to stderr to ensure visibility
                # even if stdout is being overwritten by Live displays
                if record.levelno >= logging.ERROR and record.exc_info:
                    # Print to stderr as well to avoid being overwritten by Live displays
                    stderr_console = Console(file=sys.stderr, width=self.console.width)
                    stderr_console.print(log_renderable, crop=False, overflow="ignore")
                
                # Print without height limit to show full tracebacks
                # Use crop=False to prevent truncation, and ensure full output
                self.console.print(log_renderable, crop=False, overflow="ignore")
            except Exception:
                self.handleError(record)
            finally:
                if hashable:
                    self._logged_exceptions.add(hashable)


# =============================================================================
# Log database query helpers
# =============================================================================

LOGS_DEFAULT_COUNT = 500
LOGS_MAX_COUNT = 5000
LOGS_ALLOWED_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "ALERT"}


def normalize_log_levels(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    levels: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            return None
        level = entry.strip().upper()
        if level not in LOGS_ALLOWED_LEVELS:
            return None
        levels.append(level)
    return levels


def normalize_log_audience(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    audience = value.strip().lower()
    allowed = {member.value for member in Log.Audience}
    return audience if audience in allowed else None


def load_build_logs(
    *,
    build_id: str,
    stage: str | None,
    log_levels: list[str] | None,
    audience: str | None,
    count: int,
) -> list[dict[str, Any]]:
    count = max(1, min(count, LOGS_MAX_COUNT))
    db_path = BuildLogger.get_log_db()
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row

    where_clauses = ["logs.build_id = ?"]
    params: list[Any] = [build_id]

    if stage:
        where_clauses.append("logs.stage = ?")
        params.append(stage)

    if log_levels:
        placeholders = ", ".join(["?"] * len(log_levels))
        where_clauses.append(f"logs.level IN ({placeholders})")
        params.extend(log_levels)

    if audience:
        where_clauses.append("logs.audience = ?")
        params.append(audience)

    where_sql = " AND ".join(where_clauses)
    query = f"""
        SELECT logs.timestamp, logs.level, logs.audience, logs.logger_name,
               logs.message, logs.ato_traceback, logs.python_traceback, logs.objects
        FROM logs
        WHERE {where_sql}
        ORDER BY logs.id DESC
        LIMIT ?
    """

    params.append(count)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    results: list[dict[str, Any]] = []
    for row in rows:
        objects = None
        if row["objects"]:
            try:
                objects = json.loads(row["objects"])
            except json.JSONDecodeError:
                objects = None
        results.append(
            {
                "timestamp": row["timestamp"],
                "level": row["level"],
                "audience": row["audience"],
                "logger_name": row["logger_name"],
                "message": row["message"],
                "ato_traceback": row["ato_traceback"],
                "python_traceback": row["python_traceback"],
                "objects": objects,
            }
        )

    return results


def load_test_logs(
    *,
    test_run_id: str,
    test_name: str | None,
    log_levels: list[str] | None,
    audience: str | None,
    count: int,
) -> list[dict[str, Any]]:
    """Load test logs from the test log database."""
    count = max(1, min(count, LOGS_MAX_COUNT))
    db_path = TestLogger.get_log_db()
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row

    where_clauses = ["test_logs.test_run_id = ?"]
    params: list[Any] = [test_run_id]

    if test_name:
        where_clauses.append("test_logs.test_name LIKE ?")
        params.append(f"%{test_name}%")

    if log_levels:
        placeholders = ", ".join(["?"] * len(log_levels))
        where_clauses.append(f"test_logs.level IN ({placeholders})")
        params.extend(log_levels)

    if audience:
        where_clauses.append("test_logs.audience = ?")
        params.append(audience)

    where_sql = " AND ".join(where_clauses)
    query = f"""
        SELECT test_logs.timestamp, test_logs.level, test_logs.audience,
               test_logs.logger_name, test_logs.message, test_logs.ato_traceback,
               test_logs.python_traceback, test_logs.objects, test_logs.test_name
        FROM test_logs
        WHERE {where_sql}
        ORDER BY test_logs.id DESC
        LIMIT ?
    """

    params.append(count)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    results: list[dict[str, Any]] = []
    for row in rows:
        objects = None
        if row["objects"]:
            try:
                objects = json.loads(row["objects"])
            except json.JSONDecodeError:
                objects = None
        results.append(
            {
                "timestamp": row["timestamp"],
                "level": row["level"],
                "audience": row["audience"],
                "logger_name": row["logger_name"],
                "message": row["message"],
                "ato_traceback": row["ato_traceback"],
                "python_traceback": row["python_traceback"],
                "objects": objects,
                "test_name": row["test_name"],
            }
        )

    return results


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

# Module-level exports for convenience
get_exception_display_message = BaseLogger.get_exception_display_message
