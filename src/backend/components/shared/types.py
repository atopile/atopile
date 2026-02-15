from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeAlias

JSONPrimitive: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
JSONDict: TypeAlias = dict[str, JSONValue]
ReadonlyJSONDict: TypeAlias = Mapping[str, JSONValue]


def is_json_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def test_is_json_mapping() -> None:
    assert is_json_mapping({})
    assert not is_json_mapping([])
