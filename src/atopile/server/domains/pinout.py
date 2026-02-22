"""Pinout domain logic - reads pinout JSON build artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PINOUT_FILE = Path("pinout") / "pinout.json"


def _pinout_path(project_path: Path, target: str) -> Path:
    return project_path / "build" / "builds" / target / _PINOUT_FILE


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid JSON in {path}: expected JSON object")
    return data


def handle_get_pinout(
    project_root: str, target: str = "default"
) -> dict[str, Any] | None:
    """Get pinout data for a build target."""
    project_path = Path(project_root)
    if not project_path.exists():
        raise ValueError(f"Project path does not exist: {project_root}")

    if not (project_path / "ato.yaml").exists():
        raise ValueError(f"No ato.yaml found in: {project_root}")

    pinout_path = _pinout_path(project_path, target)
    if not pinout_path.exists():
        return None
    return _read_json_object(pinout_path)


__all__ = [
    "handle_get_pinout",
]
