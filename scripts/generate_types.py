#!/usr/bin/env python3
"""Generate TypeScript types from shared CamelModel schemas."""

from __future__ import annotations

import json
import re
import types
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel

import atopile.dataclasses as dataclasses_module
import atopile.server.ui.store as store_module
from atopile.dataclasses import CamelModel
from atopile.server.ui.store import STORE_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src/ui/shared/generated-types.ts"


def main() -> None:
    models = discover_camel_models()
    enums = discover_enums(models)

    lines: list[str] = [
        "// Generated from src/atopile/dataclasses.py by scripts/generate_types.py",
        "// Do not edit by hand.",
        "",
        "type JsonPrimitive = string | number | boolean | null;",
        "export type JsonValue ="
        " JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };",
        "",
        "function cloneGenerated<T>(value: T): T {",
        "  return JSON.parse(JSON.stringify(value)) as T;",
        "}",
        "",
    ]

    for enum_cls in enums:
        lines.extend(render_enum(enum_cls))
        lines.append("")

    for model in models:
        lines.extend(render_model(model))
        lines.append("")

    lines.extend(render_store_keys())
    lines.append("")

    for model in models:
        default = instantiate_default(model)
        if default is None:
            continue
        payload = json.dumps(default, indent=2, sort_keys=True)
        lines.extend(
            [
                f"export const DEFAULT_{model.__name__}: {model.__name__} = {payload};",
                "",
                f"export function create{model.__name__}(): {model.__name__} {{",
                f"  return cloneGenerated(DEFAULT_{model.__name__});",
                "}",
                "",
            ]
        )

    OUT.write_text("\n".join(lines).rstrip() + "\n")


def discover_camel_models() -> list[type[CamelModel]]:
    models: list[type[CamelModel]] = []
    for module in (dataclasses_module, store_module):
        for value in vars(module).values():
            if not isinstance(value, type):
                continue
            if not issubclass(value, CamelModel) or value is CamelModel:
                continue
            if value.__module__ != module.__name__:
                continue
            models.append(value)
    return sorted(
        {model.__name__: model for model in models}.values(),
        key=lambda model: model.__name__,
    )


def discover_enums(models: list[type[CamelModel]]) -> list[type[Enum]]:
    enums: dict[str, type[Enum]] = {}
    for model in models:
        for field in model.model_fields.values():
            collect_enums(field.annotation, enums)
    return sorted(enums.values(), key=lambda enum_cls: enum_cls.__name__)


def collect_enums(annotation: Any, enums: dict[str, type[Enum]]) -> None:
    if annotation is Any:
        return

    origin = get_origin(annotation)
    if origin is Annotated:
        collect_enums(get_args(annotation)[0], enums)
        return

    if origin in {Union, types.UnionType, list, tuple, set, frozenset}:
        for arg in get_args(annotation):
            collect_enums(arg, enums)
        return

    if origin in {dict, type(dict), Literal}:
        return

    if isinstance(annotation, type):
        if issubclass(annotation, Enum):
            enums[annotation.__name__] = annotation
            return
        if issubclass(annotation, BaseModel) and not issubclass(annotation, CamelModel):
            raise RuntimeError(
                "CamelModel field references non-CamelModel"
                f" schema: {annotation.__name__}"
            )


def render_enum(enum_cls: type[Enum]) -> list[str]:
    literals = " | ".join(json.dumps(member.value) for member in enum_cls)
    return [f"export type {enum_cls.__name__} = {literals};"]


def render_model(model: type[BaseModel]) -> list[str]:
    lines = [f"export interface {model.__name__} {{"]
    serialize_by_alias = bool(model.model_config.get("serialize_by_alias"))

    for field_name, field in model.model_fields.items():
        if field.exclude is True:
            continue
        ts_name = (
            (field.serialization_alias or field_name)
            if serialize_by_alias
            else field_name
        )
        ts_type = override_model_field_ts_type(model.__name__, field_name)
        if ts_type is None:
            ts_type = annotation_to_ts(field.annotation)
        lines.append(f"  {format_property_name(ts_name)}: {ts_type};")

    if model.model_config.get("extra") == "allow":
        lines.append("  [key: string]: unknown;")

    lines.append("}")
    return lines


def override_model_field_ts_type(model_name: str, field_name: str) -> str | None:
    if model_name == "UiSubscribeMessage" and field_name == "keys":
        return "StoreKey[]"
    if model_name == "UiStateMessage" and field_name == "key":
        return "StoreKey"
    return None


def render_store_keys() -> list[str]:
    store_fields = _all_store_fields()
    keys = [store_field.wire_key for _, store_field in store_fields]
    key_literals = ", ".join(json.dumps(key) for key in keys)
    return [
        f"export const STORE_KEYS = [{key_literals}] as const;",
        "export type StoreKey = typeof STORE_KEYS[number];",
    ]


def _all_store_fields() -> list[Any]:
    return sorted(
        [
            (field_name, store_field)
            for field_name, store_field in STORE_SCHEMA.items()
            if getattr(store_field, "wire_key", None)
        ],
        key=lambda item: item[0],
    )


def instantiate_default(model: type[BaseModel]) -> dict[str, Any] | list[Any] | None:
    try:
        instance = model()
    except Exception:
        return None
    return instance.model_dump(mode="json")


def annotation_to_ts(annotation: Any) -> str:
    if annotation is Any:
        return "unknown"

    origin = get_origin(annotation)
    if origin is Annotated:
        return annotation_to_ts(get_args(annotation)[0])

    if origin in {list, tuple, set, frozenset}:
        item_type = annotation_to_ts(
            get_args(annotation)[0] if get_args(annotation) else Any
        )
        return f"{wrap_array_item(item_type)}[]"

    if origin in {dict, type(dict)}:
        args = get_args(annotation)
        value_type = annotation_to_ts(args[1] if len(args) == 2 else Any)
        return f"Record<string, {value_type}>"

    if origin in {Union, types.UnionType}:
        return join_union(annotation_to_ts(arg) for arg in get_args(annotation))

    if origin is Literal:
        return " | ".join(json.dumps(arg) for arg in get_args(annotation))

    if isinstance(annotation, type):
        if issubclass(annotation, BaseModel):
            if not issubclass(annotation, CamelModel):
                raise RuntimeError(
                    "CamelModel field references non-CamelModel"
                    f" schema: {annotation.__name__}"
                )
            return annotation.__name__
        if issubclass(annotation, Enum):
            return annotation.__name__
        if annotation is str:
            return "string"
        if annotation in {int, float}:
            return "number"
        if annotation is bool:
            return "boolean"
        if annotation is type(None):
            return "null"

    return "unknown"


def join_union(items: Any) -> str:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return " | ".join(seen) if seen else "unknown"


def wrap_array_item(item_type: str) -> str:
    if " | " in item_type or " & " in item_type:
        return f"({item_type})"
    return item_type


def format_property_name(name: str) -> str:
    if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", name):
        return name
    return json.dumps(name)


if __name__ == "__main__":
    main()
