"""Reactive state store for websocket subscribers."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Callable

OnChangeCallback = Callable[[str, Any, Any], None]


def _default_state() -> dict[str, Any]:
    return {
        "coreStatus": {
            "error": None,
            "uvPath": "",
            "atoBinary": "",
            "mode": "production",
            "version": "",
            "coreServerPort": 0,
        },
        "extensionSettings": {
            "devPath": "",
            "autoInstall": True,
        },
        "projectState": {
            "selectedProject": None,
            "selectedTarget": None,
            "activeFilePath": None,
        },
        "projects": [],
        "projectFiles": [],
        "currentBuilds": [],
        "previousBuilds": [],
        "packagesSummary": {
            "packages": [],
            "total": 0,
            "installedCount": 0,
        },
        "partsSearch": {
            "parts": [],
            "error": None,
        },
        "installedParts": {
            "parts": [],
        },
        "stdlibData": {
            "items": [],
            "total": 0,
        },
        "structureData": {
            "modules": [],
            "total": 0,
        },
        "variablesData": {
            "nodes": [],
        },
        "bomData": {
            "components": [],
            "totalQuantity": 0,
            "uniqueParts": 0,
            "estimatedCost": None,
            "outOfStock": 0,
        },
    }


class Store:
    """Port of the extension hub store semantics."""

    def __init__(self) -> None:
        self._state = _default_state()
        self.on_change: OnChangeCallback | None = None

    def get(self, key: str) -> Any:
        return deepcopy(self._state[key])

    def set(self, key: str, value: Any) -> None:
        old_value = self._state[key]
        if json.dumps(old_value, sort_keys=True) == json.dumps(value, sort_keys=True):
            return
        self._state[key] = deepcopy(value)
        if self.on_change:
            self.on_change(key, deepcopy(value), deepcopy(old_value))

    def merge(self, key: str, partial: dict[str, Any]) -> None:
        old_value = self._state[key]
        value = {**old_value, **partial}
        if json.dumps(old_value, sort_keys=True) == json.dumps(value, sort_keys=True):
            return
        self._state[key] = deepcopy(value)
        if self.on_change:
            self.on_change(key, deepcopy(value), deepcopy(old_value))
