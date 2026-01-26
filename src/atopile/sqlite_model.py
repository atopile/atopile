"""
SQLite database helpers.

Provides a unified TableHelper for schema init, inserts, queries,
batched appends, and updates — all backed by a persistent WAL connection.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)

_SCHEMA_DIR = Path(__file__).parent

_WAL_PRAGMAS = (
    "journal_mode=WAL",
    "synchronous=NORMAL",
    "temp_store=MEMORY",
    "busy_timeout=30000",
)


def _read_schema(schema_name: str) -> str:
    return (_SCHEMA_DIR / schema_name).read_text()


def _build_insert(table: str, columns: list[str], *, or_replace: bool = False) -> str:
    cols = ", ".join(columns)
    ph = ", ".join("?" for _ in columns)
    verb = "INSERT OR REPLACE" if or_replace else "INSERT"
    return f"{verb} INTO {table} ({cols}) VALUES ({ph})"


class TableHelper:
    """Unified SQLite table helper with persistent WAL connection.

    Supports immediate inserts (save), batched appends, queries, and updates.
    Serialization is automatic: enums -> .value, dicts/lists -> JSON.
    """

    BATCH_SIZE = 300
    FLUSH_INTERVAL = 0.5

    def __init__(
        self,
        db_path: Path,
        schema_name: str,
        table: str,
        columns: list[str],
        *,
        pk_columns: frozenset[str] = frozenset(),
        from_row: Callable[[sqlite3.Row], Any] | None = None,
    ) -> None:
        self.table = table
        self.columns = columns
        self.pk_columns = pk_columns
        self.non_pk_columns = [c for c in columns if c not in pk_columns]
        self._from_row = from_row

        # Pre-build SQL
        self._insert_sql = _build_insert(table, columns)
        self._upsert_sql = _build_insert(table, columns, or_replace=True)
        self._append_sql = _build_insert(table, self.non_pk_columns)

        # Connection state
        self._db_path = db_path
        self._local = threading.local()

        # Append buffer
        self._buffer: list[Any] = []
        self._buffer_lock = threading.Lock()
        self._last_flush = time.monotonic()
        self._closed = False

        # Init database
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connection()
        conn.executescript(_read_schema(schema_name))
        conn.commit()

    # -- connection -----------------------------------------------------------

    def _connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self._db_path), check_same_thread=False, timeout=30.0
            )
            for pragma in _WAL_PRAGMAS:
                self._local.conn.execute(f"PRAGMA {pragma}")
        return self._local.conn

    # -- serialization --------------------------------------------------------

    def _serialize(
        self, instance: Any, columns: list[str] | None = None,
    ) -> tuple[Any, ...]:
        cols = columns or self.columns
        vals: list[Any] = []
        for col in cols:
            v = getattr(instance, col)
            if isinstance(v, Enum):
                v = v.value
            elif isinstance(v, (dict, list)):
                v = json.dumps(v)
            vals.append(v)
        return tuple(vals)

    # -- immediate writes -----------------------------------------------------

    def save(self, instance: Any, *, or_replace: bool = True) -> None:
        """Insert (or replace) a single row immediately."""
        sql = self._upsert_sql if or_replace else self._insert_sql
        conn = self._connection()
        conn.execute(sql, self._serialize(instance))
        conn.commit()

    def update(
        self,
        instance: Any,
        *,
        where: str,
        params: tuple[Any, ...] | list[Any] = (),
    ) -> int:
        """Update non-PK columns. Returns affected row count."""
        cols = self.non_pk_columns
        if not cols:
            return 0
        data = dict(zip(self.columns, self._serialize(instance)))
        set_clause = ", ".join(f"{c} = ?" for c in cols)
        sql = f"UPDATE {self.table} SET {set_clause}"
        if where:
            sql += f" WHERE {where}"
        bind = [data[c] for c in cols] + list(params)
        conn = self._connection()
        result = conn.execute(sql, bind).rowcount
        conn.commit()
        return result

    # -- batched writes -------------------------------------------------------

    def append(self, entry: Any) -> None:
        """Buffer an entry for batched insertion (non-PK columns)."""
        if self._closed:
            return
        with self._buffer_lock:
            self._buffer.append(entry)
            should_flush = (
                len(self._buffer) >= self.BATCH_SIZE
                or (time.monotonic() - self._last_flush) > self.FLUSH_INTERVAL
            )
        if should_flush:
            self.flush()

    def flush(self) -> None:
        with self._buffer_lock:
            if not self._buffer:
                return
            entries, self._buffer = self._buffer, []
            self._last_flush = time.monotonic()

        data = [self._serialize(e, self.non_pk_columns) for e in entries]
        try:
            conn = self._connection()
            conn.executemany(self._append_sql, data)
            conn.commit()
        except sqlite3.Error as e:
            self._local.conn = None
            try:
                conn = self._connection()
                conn.executemany(self._append_sql, data)
                conn.commit()
            except sqlite3.Error as e2:
                log.error(
                    "TableHelper: failed to write %d entries to %s: %s (original: %s)",
                    len(data), self._db_path, e2, e,
                )

    # -- queries --------------------------------------------------------------

    def query_all(
        self,
        *,
        where: str = "",
        params: tuple[Any, ...] | list[Any] = (),
        order_by: str = "",
        limit: int | None = None,
    ) -> list[Any]:
        """SELECT rows, optionally deserializing via from_row."""
        sql = f"SELECT * FROM {self.table}"
        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        bind: list[Any] = list(params)
        if limit is not None:
            sql += " LIMIT ?"
            bind.append(limit)
        conn = self._connection()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, bind).fetchall()
        if self._from_row:
            return [self._from_row(r) for r in rows]
        return list(rows)

    def query_one(
        self,
        *,
        where: str = "",
        params: tuple[Any, ...] | list[Any] = (),
        order_by: str = "",
    ) -> Any | None:
        """Like query_all but returns the first result or None."""
        results = self.query_all(
            where=where, params=params, order_by=order_by, limit=1,
        )
        return results[0] if results else None

    # -- raw SQL --------------------------------------------------------------

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        """Run arbitrary SQL on the underlying connection."""
        try:
            conn = self._connection()
            conn.execute(sql, params)
            conn.commit()
        except sqlite3.Error:
            pass

    # -- lifecycle ------------------------------------------------------------

    def close(self) -> None:
        self._closed = True
        self.flush()
        if hasattr(self._local, "conn") and self._local.conn:
            try:
                self._local.conn.close()
            except sqlite3.Error:
                pass
            self._local.conn = None


# ---------------------------------------------------------------------------
# Log column definitions
# ---------------------------------------------------------------------------

LOG_COLUMNS = [
    "build_id", "timestamp", "stage", "level", "message",
    "logger_name", "audience", "source_file", "source_line",
    "ato_traceback", "python_traceback", "objects",
]

TEST_LOG_COLUMNS = [
    "test_run_id", "timestamp", "test_name", "level", "message",
    "logger_name", "audience", "source_file", "source_line",
    "ato_traceback", "python_traceback", "objects",
]
