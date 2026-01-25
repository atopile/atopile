"""
SQLite helpers for Pydantic models and Pydantic dataclasses.
"""

from __future__ import annotations

import json
from dataclasses import MISSING, fields, is_dataclass
from enum import Enum
from typing import Any, ClassVar, get_args, get_origin, get_type_hints

from pydantic import BaseModel, TypeAdapter

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
        json_schema_extra: dict[str, Any] | None,
    ) -> None:
        self.annotation = annotation
        self.default = default
        self.json_schema_extra = json_schema_extra


def _model_fields(model_cls: type[Any]) -> dict[str, _FieldInfo]:
    if isinstance(model_cls, type) and issubclass(model_cls, BaseModel):
        return {
            name: _FieldInfo(
                field.annotation,
                field.default,
                field.json_schema_extra,  # type: ignore[arg-type]
            )
            for name, field in model_cls.model_fields.items()
        }

    if is_dataclass(model_cls):
        hints = get_type_hints(model_cls, include_extras=True)
        result: dict[str, _FieldInfo] = {}
        for f in fields(model_cls):
            annotation = hints.get(f.name, f.type)
            default = f.default if f.default is not MISSING else MISSING
            metadata = f.metadata or {}
            json_schema_extra = (
                metadata.get("sqlite") or metadata.get("json_schema_extra")
            )
            result[f.name] = _FieldInfo(annotation, default, json_schema_extra)
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
    return getattr(model_cls, "__indexes__", [])


def create_table_sql(model_cls: type[Any]) -> str:
    """Generate CREATE TABLE SQL from a model class."""
    table = _get_tablename(model_cls)
    columns: list[str] = []
    for field_name, field_info in _model_fields(model_cls).items():
        annotation = field_info.annotation
        sqlite_type = "TEXT" if annotation is None else _python_type_to_sqlite(annotation)

        col_def = f"{field_name} {sqlite_type}"

        json_schema = field_info.json_schema_extra or {}
        if isinstance(json_schema, dict):
            if json_schema.get("primary_key"):
                col_def += " PRIMARY KEY"
                if json_schema.get("autoincrement"):
                    col_def += " AUTOINCREMENT"
            if json_schema.get("unique"):
                col_def += " UNIQUE"
            if json_schema.get("not_null"):
                col_def += " NOT NULL"

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
    return [c for c in _model_fields(model_cls).keys() if c not in exclude]


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
