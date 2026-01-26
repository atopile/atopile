"""
SQLite database helpers.

Provides:
- Per-table typed helpers for serialization, insertion, and querying
- Schema initialization scoped to specific tables
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Generic, Iterator, TypeVar

log = logging.getLogger(__name__)

T = TypeVar("T")

# ===========================================================================
# Connection
# ===========================================================================


@contextmanager
def connect(db_path: Path, *, timeout: float = 5.0) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection, commit on success, close on exit."""
    conn = sqlite3.connect(str(db_path), timeout=timeout)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ===========================================================================
# Schema
# ===========================================================================

_SCHEMA_DIR = Path(__file__).parent


def read_schema(schema_name: str) -> str:
    """Read a .sql schema file and return its contents."""
    return (_SCHEMA_DIR / schema_name).read_text()


def init_db(db_path: Path, schema_name: str) -> None:
    """Create tables from a .sql file, creating parent dirs as needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn:
        conn.executescript(read_schema(schema_name))


# ===========================================================================
# Raw execute
# ===========================================================================


def execute(
    db_path: Path,
    sql: str,
    params: tuple[Any, ...] | list[Any] = (),
) -> int:
    """Execute arbitrary SQL and return the number of affected rows."""
    with connect(db_path) as conn:
        return conn.execute(sql, params).rowcount


# ===========================================================================
# Generic table helper
# ===========================================================================


class TableHelper(Generic[T]):
    """Typed helper for a single SQLite table.

    Provides save, query, and update operations with explicit
    serialization / deserialization callbacks.
    """

    def __init__(
        self,
        table: str,
        columns: list[str],
        to_tuple: Callable[[T], tuple[Any, ...]],
        from_row: Callable[[sqlite3.Row], T],
        *,
        pk_columns: frozenset[str] = frozenset(),
    ) -> None:
        self.table = table
        self.columns = columns
        self.to_tuple = to_tuple
        self.from_row = from_row
        self.pk_columns = pk_columns
        self.non_pk_columns = [c for c in columns if c not in pk_columns]

        # Pre-build SQL -------------------------------------------------------
        cols = ", ".join(columns)
        ph = ", ".join("?" for _ in columns)
        self.insert_all_sql = f"INSERT INTO {table} ({cols}) VALUES ({ph})"
        self.insert_or_replace_sql = (
            f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({ph})"
        )

        non_pk = self.non_pk_columns
        self.insert_non_pk_sql = (
            f"INSERT INTO {table} ({', '.join(non_pk)}) VALUES "
            f"({', '.join('?' for _ in non_pk)})"
        )

    # -- helpers --------------------------------------------------------------

    def _to_dict(self, instance: T) -> dict[str, Any]:
        return dict(zip(self.columns, self.to_tuple(instance)))

    # -- mutations ------------------------------------------------------------

    def save(
        self,
        db_path: Path,
        instance: T,
        *,
        or_replace: bool = True,
    ) -> None:
        """Insert (or replace) a single row."""
        sql = self.insert_or_replace_sql if or_replace else self.insert_all_sql
        with connect(db_path) as conn:
            conn.execute(sql, self.to_tuple(instance))

    def update(
        self,
        db_path: Path,
        instance: T,
        *,
        where: str,
        params: tuple[Any, ...] | list[Any] = (),
    ) -> int:
        """Update rows, setting all non-PK fields from *instance*.

        Returns the number of affected rows.
        """
        data = self._to_dict(instance)
        cols = self.non_pk_columns
        if not cols:
            return 0

        set_clause = ", ".join(f"{c} = ?" for c in cols)
        sql = f"UPDATE {self.table} SET {set_clause}"
        if where:
            sql += f" WHERE {where}"

        bind = [data[c] for c in cols] + list(params)
        with connect(db_path) as conn:
            return conn.execute(sql, bind).rowcount

    # -- queries --------------------------------------------------------------

    def query_all(
        self,
        db_path: Path,
        *,
        where: str = "",
        params: tuple[Any, ...] | list[Any] = (),
        order_by: str = "",
        limit: int | None = None,
    ) -> list[T]:
        """SELECT rows and return typed model instances."""
        sql = f"SELECT * FROM {self.table}"
        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"

        bind: list[Any] = list(params)
        if limit is not None:
            sql += " LIMIT ?"
            bind.append(limit)

        with connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, bind).fetchall()
        return [self.from_row(r) for r in rows]

    def query_one(
        self,
        db_path: Path,
        *,
        where: str = "",
        params: tuple[Any, ...] | list[Any] = (),
        order_by: str = "",
    ) -> T | None:
        """Like :meth:`query_all` but returns the first result or ``None``."""
        results = self.query_all(
            db_path, where=where, params=params, order_by=order_by, limit=1
        )
        return results[0] if results else None


# ===========================================================================
# Per-table helpers
# ===========================================================================

# ---------------------------------------------------------------------------
# build_history  (HistoricalBuild)
# ---------------------------------------------------------------------------


def _historical_build_to_tuple(b: Any) -> tuple[Any, ...]:
    return (
        b.build_id,
        b.project_root,
        b.target,
        b.entry,
        b.status.value,
        b.return_code,
        b.error,
        b.started_at,
        b.duration,
        json.dumps(b.stages),
        b.warnings,
        b.errors,
        b.completed_at,
    )


def _historical_build_from_row(row: sqlite3.Row) -> Any:
    from atopile.dataclasses import BuildStatus, HistoricalBuild

    return HistoricalBuild(
        build_id=row["build_id"],
        project_root=row["project_root"],
        target=row["target"],
        entry=row["entry"],
        status=BuildStatus(row["status"]),
        return_code=row["return_code"],
        error=row["error"],
        started_at=row["started_at"],
        duration=row["duration"],
        stages=json.loads(row["stages"]) if row["stages"] else [],
        warnings=row["warnings"],
        errors=row["errors"],
        completed_at=row["completed_at"],
    )


historical_builds = TableHelper(
    table="build_history",
    columns=[
        "build_id", "project_root", "target", "entry", "status",
        "return_code", "error", "started_at", "duration", "stages",
        "warnings", "errors", "completed_at",
    ],
    to_tuple=_historical_build_to_tuple,
    from_row=_historical_build_from_row,
    pk_columns=frozenset({"build_id"}),
)


# ---------------------------------------------------------------------------
# builds  (BuildRow)
# ---------------------------------------------------------------------------


def _build_row_to_tuple(b: Any) -> tuple[Any, ...]:
    return (b.build_id, b.project_path, b.target, b.timestamp, b.created_at)


def _build_row_from_row(row: sqlite3.Row) -> Any:
    from atopile.dataclasses import BuildRow

    return BuildRow(
        build_id=row["build_id"],
        project_path=row["project_path"],
        target=row["target"],
        timestamp=row["timestamp"],
        created_at=row["created_at"],
    )


build_rows = TableHelper(
    table="builds",
    columns=["build_id", "project_path", "target", "timestamp", "created_at"],
    to_tuple=_build_row_to_tuple,
    from_row=_build_row_from_row,
    pk_columns=frozenset({"build_id"}),
)


# ---------------------------------------------------------------------------
# logs  (LogRow)
# ---------------------------------------------------------------------------


def _log_row_to_tuple(r: Any) -> tuple[Any, ...]:
    return (
        r.id, r.build_id, r.timestamp, r.stage, r.level, r.message,
        r.logger_name, r.audience, r.source_file, r.source_line,
        r.ato_traceback, r.python_traceback, r.objects,
    )


def _log_row_from_row(row: sqlite3.Row) -> Any:
    from atopile.dataclasses import LogRow

    return LogRow(
        build_id=row["build_id"],
        timestamp=row["timestamp"],
        stage=row["stage"],
        level=row["level"],
        message=row["message"],
        logger_name=row["logger_name"],
        audience=row["audience"],
        source_file=row["source_file"],
        source_line=row["source_line"],
        ato_traceback=row["ato_traceback"],
        python_traceback=row["python_traceback"],
        objects=row["objects"],
    )


log_rows = TableHelper(
    table="logs",
    columns=[
        "id", "build_id", "timestamp", "stage", "level", "message",
        "logger_name", "audience", "source_file", "source_line",
        "ato_traceback", "python_traceback", "objects",
    ],
    to_tuple=_log_row_to_tuple,
    from_row=_log_row_from_row,
    pk_columns=frozenset({"id"}),
)


# ---------------------------------------------------------------------------
# test_runs  (TestRunRow)
# ---------------------------------------------------------------------------


def _test_run_row_to_tuple(r: Any) -> tuple[Any, ...]:
    return (r.test_run_id, r.created_at)


def _test_run_row_from_row(row: sqlite3.Row) -> Any:
    from atopile.dataclasses import TestRunRow

    return TestRunRow(
        test_run_id=row["test_run_id"],
        created_at=row["created_at"],
    )


test_run_rows = TableHelper(
    table="test_runs",
    columns=["test_run_id", "created_at"],
    to_tuple=_test_run_row_to_tuple,
    from_row=_test_run_row_from_row,
    pk_columns=frozenset({"test_run_id"}),
)


# ---------------------------------------------------------------------------
# test_logs  (TestLogRow)
# ---------------------------------------------------------------------------


def _test_log_row_to_tuple(r: Any) -> tuple[Any, ...]:
    return (
        r.id, r.test_run_id, r.timestamp, r.test_name, r.level, r.message,
        r.logger_name, r.audience, r.source_file, r.source_line,
        r.ato_traceback, r.python_traceback, r.objects,
    )


def _test_log_row_from_row(row: sqlite3.Row) -> Any:
    from atopile.dataclasses import TestLogRow

    return TestLogRow(
        test_run_id=row["test_run_id"],
        timestamp=row["timestamp"],
        test_name=row["test_name"],
        level=row["level"],
        message=row["message"],
        logger_name=row["logger_name"],
        audience=row["audience"],
        source_file=row["source_file"],
        source_line=row["source_line"],
        ato_traceback=row["ato_traceback"],
        python_traceback=row["python_traceback"],
        objects=row["objects"],
    )


test_log_rows = TableHelper(
    table="test_logs",
    columns=[
        "id", "test_run_id", "timestamp", "test_name", "level", "message",
        "logger_name", "audience", "source_file", "source_line",
        "ato_traceback", "python_traceback", "objects",
    ],
    to_tuple=_test_log_row_to_tuple,
    from_row=_test_log_row_from_row,
    pk_columns=frozenset({"id"}),
)
