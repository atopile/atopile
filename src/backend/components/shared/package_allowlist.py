from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .package_normalization import normalize_package

_DEFAULT_ALLOWLIST_PATH = Path(__file__).with_name("package_allowlist.generated.json")


@lru_cache(maxsize=1)
def _load_allowlist_payload(path: str) -> dict[str, Any]:
    allowlist_path = Path(path)
    if not allowlist_path.exists():
        return {}
    raw = json.loads(allowlist_path.read_text())
    if not isinstance(raw, dict):
        return {}
    return raw


@lru_cache(maxsize=1)
def _normalized_allowlists(path: str) -> dict[str, set[str]]:
    payload = _load_allowlist_payload(path)
    raw_allowlists = payload.get("allowlists")
    if not isinstance(raw_allowlists, dict):
        return {}

    out: dict[str, set[str]] = {}
    for component_type, packages in raw_allowlists.items():
        if not isinstance(component_type, str) or not isinstance(packages, list):
            continue
        normalized_set: set[str] = set()
        for package in packages:
            if not isinstance(package, str):
                continue
            normalized = normalize_package(component_type, package)
            if normalized:
                normalized_set.add(normalized)
        out[component_type] = normalized_set
    return out


def is_known_package(
    component_type: str,
    package: str,
    *,
    allowlist_path: Path = _DEFAULT_ALLOWLIST_PATH,
) -> bool:
    normalized = normalize_package(component_type, package)
    if normalized is None:
        return False
    allowlists = _normalized_allowlists(str(allowlist_path))
    allowed = allowlists.get(component_type)
    if not allowed:
        return False
    return normalized in allowed


def has_component_type_allowlist(
    component_type: str,
    *,
    allowlist_path: Path = _DEFAULT_ALLOWLIST_PATH,
) -> bool:
    allowlists = _normalized_allowlists(str(allowlist_path))
    return component_type in allowlists


def get_known_packages(
    component_type: str,
    *,
    allowlist_path: Path = _DEFAULT_ALLOWLIST_PATH,
) -> list[str]:
    allowlists = _normalized_allowlists(str(allowlist_path))
    return sorted(allowlists.get(component_type, set()))


def get_allowlist_payload(
    *,
    allowlist_path: Path = _DEFAULT_ALLOWLIST_PATH,
) -> dict[str, Any]:
    payload = _load_allowlist_payload(str(allowlist_path))
    if not payload:
        return {
            "available": False,
            "allowlists": {},
            "summary": {
                "component_types": 0,
                "selected_package_entries": 0,
                "selected_unique_packages": 0,
            },
        }
    return {
        "available": True,
        **payload,
    }
