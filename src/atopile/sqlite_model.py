"""
SQLite helpers for Pydantic models and Pydantic dataclasses.

Provides:
- Schema generation from model classes (create_table_sql)
- Row serialization / deserialization (to_row_dict, from_row)
- Connection-managed helpers for common DB operations (save, query_all, …)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import MISSING, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterator, get_args, get_origin, get_type_hints

from pydantic import BaseModel, TypeAdapter

log = logging.getLogger(__name__)

_TYPE_MAP: dict[type, str] = {
    int: "INTEGER",
    float: "REAL",
    str: "TEXT",
    bool: "INTEGER",
    bytes: "BLOB",
}


class _FieldInfo:
    def __init__(
        self,
        annotation: Any,
        default: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.annotation = annotation
        self.default = default
        self.metadata = metadata or {}


def _model_fields(model_cls: type[Any]) -> dict[str, _FieldInfo]:
    if isinstance(model_cls, type) and issubclass(model_cls, BaseModel):
        return {
            name: _FieldInfo(
                field.annotation,
                field.default,
            )
            for name, field in model_cls.model_fields.items()
        }

    if is_dataclass(model_cls):
        hints = get_type_hints(model_cls, include_extras=True)
        result: dict[str, _FieldInfo] = {}
        for f in fields(model_cls):
            annotation = hints.get(f.name, f.type)
            default = f.default if f.default is not MISSING else MISSING
            result[f.name] = _FieldInfo(annotation, default, dict(f.metadata) if f.metadata else None)
        return result

    raise TypeError(f"Unsupported model type: {model_cls!r}")


def _python_type_to_sqlite(py_type: type) -> str:
    origin = get_origin(py_type)
    if origin is not None:
        args = get_args(py_type)
        non_none_args = [a for a in args if a is not type(None)]
        if non_none_args:
            return _python_type_to_sqlite(non_none_args[0])

    if py_type in (list, dict) or origin in (list, dict):
        return "TEXT"

    if py_type in _TYPE_MAP:
        return _TYPE_MAP[py_type]

    return "TEXT"


def _get_tablename(model_cls: type[Any]) -> str:
    table = getattr(model_cls, "__tablename__", "")
    if not table:
        raise ValueError(f"Model {model_cls.__name__} must define __tablename__")
    return table


def _get_indexes(model_cls: type[Any]) -> list[tuple[str, ...]]:
    """Extract index definitions from field metadata.

    Fields with ``metadata={"index": True}`` get single-column indexes.
    Fields with ``metadata={"index": "group_name"}`` sharing the same group
    form a composite index (ordered by field declaration order).
    """
    if not is_dataclass(model_cls):
        return []

    single: list[tuple[str, ...]] = []
    composite: dict[str, list[str]] = {}

    for f in fields(model_cls):
        index = (f.metadata or {}).get("index")
        if index is True:
            single.append((f.name,))
        elif isinstance(index, str):
            composite.setdefault(index, []).append(f.name)

    return single + [tuple(cols) for cols in composite.values()]


def create_table_sql(model_cls: type[Any]) -> str:
    """Generate CREATE TABLE SQL from a model class."""
    table = _get_tablename(model_cls)
    columns: list[str] = []
    for field_name, field_info in _model_fields(model_cls).items():
        annotation = field_info.annotation
        sqlite_type = "TEXT" if annotation is None else _python_type_to_sqlite(annotation)

        col_def = f"{field_name} {sqlite_type}"

        if field_info.metadata.get("primary_key"):
            col_def += " PRIMARY KEY"

        if field_info.default is not MISSING and not callable(field_info.default):
            if field_info.default is None:
                columns.append(col_def)
                continue
            default = field_info.default
            if isinstance(default, str):
                col_def += f" DEFAULT '{default}'"
            elif isinstance(default, bool):
                col_def += f" DEFAULT {1 if default else 0}"
            elif isinstance(default, (int, float)):
                col_def += f" DEFAULT {default}"

        columns.append(col_def)

    sql = f"CREATE TABLE IF NOT EXISTS {table} (\n"
    sql += ",\n".join(f"    {col}" for col in columns)
    sql += "\n);\n"

    for idx_cols in _get_indexes(model_cls):
        idx_name = f"idx_{table}_{'_'.join(idx_cols)}"
        cols_str = ", ".join(idx_cols)
        sql += f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({cols_str});\n"

    return sql


def insert_columns(model_cls: type[Any], *, exclude: set[str] | None = None) -> list[str]:
    if exclude is None:
        exclude = set()
    return [
        name
        for name, info in _model_fields(model_cls).items()
        if name not in exclude and not info.metadata.get("primary_key")
    ]


def insert_sql(model_cls: type[Any], columns: list[str] | None = None) -> str:
    if columns is None:
        columns = list(_model_fields(model_cls).keys())
    placeholders = ", ".join("?" * len(columns))
    cols_str = ", ".join(columns)
    return f"INSERT INTO {_get_tablename(model_cls)} ({cols_str}) VALUES ({placeholders})"


def insert_or_replace_sql(model_cls: type[Any], columns: list[str] | None = None) -> str:
    if columns is None:
        columns = list(_model_fields(model_cls).keys())
    placeholders = ", ".join("?" * len(columns))
    cols_str = ", ".join(columns)
    return (
        f"INSERT OR REPLACE INTO {_get_tablename(model_cls)} "
        f"({cols_str}) VALUES ({placeholders})"
    )


def from_row(model_cls: type[Any], row: Any) -> Any:
    """Construct a model instance from a sqlite3.Row or dict."""
    if hasattr(row, "keys"):
        data = {k: row[k] for k in row.keys()}
    elif isinstance(row, dict):
        data = row
    else:
        raise TypeError(f"Expected Row or dict, got {type(row)}")

    for field_name, field_info in _model_fields(model_cls).items():
        if field_name not in data:
            continue

        annotation = field_info.annotation
        origin = get_origin(annotation)

        actual_type = annotation
        if origin is not None:
            args = get_args(annotation)
            non_none_args = [a for a in args if a is not type(None)]
            if non_none_args:
                actual_type = non_none_args[0]
                origin = get_origin(actual_type)

        if actual_type in (list, dict) or origin in (list, dict):
            value = data[field_name]
            if isinstance(value, str):
                try:
                    data[field_name] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    data[field_name] = [] if origin is list else {}
            elif value is None:
                data[field_name] = [] if actual_type is list or origin is list else {}

    if isinstance(model_cls, type) and issubclass(model_cls, BaseModel):
        return model_cls.model_validate(data)
    return TypeAdapter(model_cls).validate_python(data)


def to_row_dict(instance: Any) -> dict[str, Any]:
    """Convert a model instance to dict for database insertion."""
    model_cls = type(instance)
    if isinstance(instance, BaseModel):
        data = instance.model_dump()
    else:
        data = TypeAdapter(model_cls).dump_python(instance)

    for field_name, field_info in _model_fields(model_cls).items():
        if field_name not in data:
            continue

        value = data[field_name]
        annotation = field_info.annotation
        origin = get_origin(annotation)

        actual_type = annotation
        if origin is not None:
            args = get_args(annotation)
            non_none_args = [a for a in args if a is not type(None)]
            if non_none_args:
                actual_type = non_none_args[0]
                origin = get_origin(actual_type)

        if isinstance(value, Enum):
            data[field_name] = value.value
        elif actual_type in (list, dict) or origin in (list, dict):
            if value is not None:
                data[field_name] = json.dumps(value)

    return data


def to_row_tuple(instance: Any, columns: list[str] | None = None) -> tuple[Any, ...]:
    data = to_row_dict(instance)
    if columns is None:
        columns = list(_model_fields(type(instance)).keys())
    return tuple(data.get(col) for col in columns)


# =============================================================================
# Connection-managed helpers
# =============================================================================


@contextmanager
def _connect(db_path: Path, *, timeout: float = 5.0) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection, commit on success, close on exit."""
    conn = sqlite3.connect(str(db_path), timeout=timeout)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path, model_cls: type[Any], *, extra_sql: str = "") -> None:
    """Create the table (and indexes) for *model_cls*, creating parent dirs."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript(create_table_sql(model_cls) + extra_sql)


def save(
    db_path: Path,
    instance: Any,
    *,
    exclude: set[str] | None = None,
    or_replace: bool = True,
) -> None:
    """
    Insert (or replace) a single row into the table for *instance*'s class.

    Args:
        db_path: Path to the SQLite database file.
        instance: A model instance whose fields map to the table columns.
        exclude: Column names to skip. Primary key fields are auto-excluded.
        or_replace: Use INSERT OR REPLACE instead of plain INSERT.
    """
    model_cls = type(instance)
    cols = insert_columns(model_cls, exclude=exclude or set())
    sql = insert_or_replace_sql(model_cls, cols) if or_replace else insert_sql(model_cls, cols)
    values = to_row_tuple(instance, cols)
    with _connect(db_path) as conn:
        conn.execute(sql, values)


def query_all(
    db_path: Path,
    model_cls: type[Any],
    *,
    where: str = "",
    params: tuple[Any, ...] | list[Any] = (),
    order_by: str = "",
    limit: int | None = None,
) -> list[Any]:
    """
    Run a SELECT on *model_cls*'s table and return typed model instances.

    Args:
        db_path: Path to the SQLite database file.
        model_cls: The model class to deserialize rows into.
        where: Optional WHERE clause **without** the ``WHERE`` keyword
               (e.g. ``"status = ? AND project_root = ?"``).
        params: Bind parameters for the WHERE clause.
        order_by: Optional ORDER BY clause **without** the keyword
                  (e.g. ``"started_at DESC"``).
        limit: Optional row limit.
    """
    table = _get_tablename(model_cls)
    sql = f"SELECT * FROM {table}"
    if where:
        sql += f" WHERE {where}"
    if order_by:
        sql += f" ORDER BY {order_by}"

    bind: list[Any] = list(params)
    if limit is not None:
        sql += " LIMIT ?"
        bind.append(limit)

    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, bind).fetchall()

    return [from_row(model_cls, r) for r in rows]


def query_one(
    db_path: Path,
    model_cls: type[Any],
    *,
    where: str = "",
    params: tuple[Any, ...] | list[Any] = (),
    order_by: str = "",
) -> Any | None:
    """Like :func:`query_all` but returns the first result or ``None``."""
    results = query_all(
        db_path, model_cls, where=where, params=params, order_by=order_by, limit=1
    )
    return results[0] if results else None


def update(
    db_path: Path,
    instance: Any,
    *,
    where: str,
    params: tuple[Any, ...] | list[Any] = (),
) -> int:
    """
    Update rows in the table for *instance*'s class.

    All non-primary-key fields are SET from the serialized instance.

    Args:
        db_path: Path to the SQLite database file.
        instance: A model instance whose fields map to the table columns.
        where: WHERE clause **without** the ``WHERE`` keyword
               (e.g. ``"build_id = ?"``).
        params: Bind parameters for the WHERE clause.

    Returns:
        Number of rows affected.
    """
    model_cls = type(instance)
    table = _get_tablename(model_cls)
    data = to_row_dict(instance)

    fields_info = _model_fields(model_cls)
    pk_cols = {
        name
        for name, info in fields_info.items()
        if info.metadata.get("primary_key")
    }
    update_cols = [c for c in data if c not in pk_cols]

    if not update_cols:
        return 0

    set_clause = ", ".join(f"{col} = ?" for col in update_cols)
    set_params = [data[col] for col in update_cols]

    sql = f"UPDATE {table} SET {set_clause}"
    if where:
        sql += f" WHERE {where}"

    bind = set_params + list(params)

    with _connect(db_path) as conn:
        cursor = conn.execute(sql, bind)
        return cursor.rowcount


def execute(
    db_path: Path,
    sql: str,
    params: tuple[Any, ...] | list[Any] = (),
) -> int:
    """
    Execute arbitrary SQL and return the number of affected rows.

    Useful for UPDATE / DELETE statements that don't map to a single model
    insert.
    """
    with _connect(db_path) as conn:
        cursor = conn.execute(sql, params)
        return cursor.rowcount
