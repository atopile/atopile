"""Reactive UI store schema for websocket-backed server state."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Mapping, TypeAlias

from pydantic import Field, TypeAdapter

from atopile.dataclasses import (
    Build,
    CamelModel,
    FileNode,
    PackagesSummaryData,
    Project,
    StdLibData,
    UiBOMData,
    UiCoreStatus,
    UiExtensionSettings,
    UiInstalledPartsData,
    UiPartsSearchData,
    UiProjectState,
    UiSidebarDetails,
    UiStructureData,
    UiVariablesData,
    _to_camel,
)

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]

OnChangeCallback = Callable[[str, JsonValue, JsonValue], None]


class UiStore(CamelModel):
    """Canonical backend-owned store schema."""

    core_status: UiCoreStatus = Field(
        default_factory=UiCoreStatus, json_schema_extra={"mergeable": True}
    )
    extension_settings: UiExtensionSettings = Field(
        default_factory=UiExtensionSettings, json_schema_extra={"mergeable": True}
    )
    project_state: UiProjectState = Field(
        default_factory=UiProjectState, json_schema_extra={"mergeable": True}
    )
    projects: list[Project] = Field(default_factory=list)
    project_files: list[FileNode] = Field(default_factory=list)
    current_builds: list[Build] = Field(default_factory=list)
    previous_builds: list[Build] = Field(default_factory=list)
    packages_summary: PackagesSummaryData = Field(
        default_factory=lambda: PackagesSummaryData(
            packages=[],
            total=0,
            installed_count=0,
        ),
        json_schema_extra={"mergeable": True},
    )
    parts_search: UiPartsSearchData = Field(
        default_factory=UiPartsSearchData, json_schema_extra={"mergeable": True}
    )
    installed_parts: UiInstalledPartsData = Field(
        default_factory=UiInstalledPartsData, json_schema_extra={"mergeable": True}
    )
    sidebar_details: UiSidebarDetails = Field(
        default_factory=UiSidebarDetails, json_schema_extra={"mergeable": True}
    )
    stdlib_data: StdLibData = Field(
        default_factory=lambda: StdLibData(items=[], total=0),
        json_schema_extra={"mergeable": True},
    )
    structure_data: UiStructureData = Field(
        default_factory=UiStructureData, json_schema_extra={"mergeable": True}
    )
    variables_data: UiVariablesData = Field(
        default_factory=UiVariablesData, json_schema_extra={"mergeable": True}
    )
    bom_data: UiBOMData = Field(
        default_factory=UiBOMData, json_schema_extra={"mergeable": True}
    )


@dataclass(frozen=True)
class StoreFieldMeta:
    wire_key: str
    adapter: TypeAdapter
    mergeable: bool


STORE_SCHEMA: dict[str, StoreFieldMeta] = {
    field_name: StoreFieldMeta(
        wire_key=model_field.serialization_alias or _to_camel(field_name),
        adapter=TypeAdapter(model_field.annotation),
        mergeable=bool((model_field.json_schema_extra or {}).get("mergeable")),
    )
    for field_name, model_field in UiStore.model_fields.items()
}
STORE_FIELDS_BY_WIRE_KEY: dict[str, str] = {
    meta.wire_key: field_name for field_name, meta in STORE_SCHEMA.items()
}


class Store:
    """Backend-owned UI store backed by the UiStore schema."""

    def __init__(self) -> None:
        self._state = UiStore()
        self.on_change: OnChangeCallback | None = None

    def get(self, field_name: str) -> Any:
        self._require_meta(field_name)
        return deepcopy(getattr(self._state, field_name))

    def dump(self, field_name: str) -> JsonValue:
        meta = self._require_meta(field_name)
        value = getattr(self._state, field_name)
        return self._dump_python(meta.adapter, value)

    def require_field_name(self, wire_key: str) -> str:
        try:
            return STORE_FIELDS_BY_WIRE_KEY[wire_key]
        except KeyError as exc:
            raise KeyError(wire_key) from exc

    def wire_key(self, field_name: str) -> str:
        return self._require_meta(field_name).wire_key

    def set(self, field_name: str, value: object) -> None:
        meta = self._require_meta(field_name)
        typed_value = meta.adapter.validate_python(value)
        old_value = self.dump(field_name)
        new_value = self._dump_python(meta.adapter, typed_value)
        if _json_equal(old_value, new_value):
            return
        setattr(self._state, field_name, typed_value)
        if self.on_change:
            self.on_change(field_name, deepcopy(new_value), deepcopy(old_value))

    def merge(self, field_name: str, partial: Mapping[str, object]) -> None:
        meta = self._require_meta(field_name)
        if not meta.mergeable:
            raise TypeError(f"Store field {meta.wire_key} is not mergeable")
        current = self.dump(field_name)
        if not isinstance(current, dict):
            raise TypeError(f"Store field {meta.wire_key} is not mergeable")
        self.set(field_name, {**current, **partial})

    @staticmethod
    def _dump_python(adapter: TypeAdapter, value: object) -> JsonValue:
        return adapter.dump_python(value, mode="json", by_alias=True)

    @staticmethod
    def _require_meta(field_name: str) -> StoreFieldMeta:
        try:
            return STORE_SCHEMA[field_name]
        except KeyError as exc:
            raise KeyError(field_name) from exc


def _json_equal(left: JsonValue, right: JsonValue) -> bool:
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)
