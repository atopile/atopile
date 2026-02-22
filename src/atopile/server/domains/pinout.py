"""Pinout domain logic - reads pinout JSON build artifacts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_PINOUT_FILE = Path("pinout") / "pinout.json"


def _require_project_path(project_root: str) -> Path:
    project_path = Path(project_root)
    if not project_path.exists():
        raise ValueError(f"Project path does not exist: {project_root}")
    return project_path


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
    project_path = _require_project_path(project_root)
    if not (project_path / "ato.yaml").exists():
        raise ValueError(f"No ato.yaml found in: {project_root}")

    pinout_path = _pinout_path(project_path, target)
    if not pinout_path.exists():
        return None
    return _read_json_object(pinout_path)


def handle_get_pinout_targets(project_root: str) -> dict[str, Any]:
    """Get available targets that have pinout data."""
    builds_dir = _require_project_path(project_root) / "build" / "builds"
    if not builds_dir.exists():
        return {"targets": [], "project_root": project_root}

    targets = sorted(
        target_dir.name
        for target_dir in builds_dir.iterdir()
        if target_dir.is_dir() and (target_dir / _PINOUT_FILE).exists()
    )
    return {"targets": targets, "project_root": project_root}


def handle_get_pinout_by_build_id(build_id: str) -> dict[str, Any] | None:
    """
    Get the pinout for a specific build by build_id.

    Looks up build info, then reads the pinout artifact file.
    """
    from atopile.model.sqlite import BuildHistory

    build_info = BuildHistory.get(build_id)
    if build_info is None:
        return None

    project_root = build_info.project_root
    target = build_info.target
    if project_root is None or target is None:
        raise ValueError(f"Build {build_id} is missing project_root or target")

    pinout_path = _pinout_path(Path(project_root), target)
    if not pinout_path.exists():
        return None

    data = _read_json_object(pinout_path)
    embedded_build_id = data.get("build_id")
    if embedded_build_id and embedded_build_id != build_id:
        log.warning(
            "Pinout build_id mismatch: expected %s, got %s",
            build_id,
            embedded_build_id,
        )
    return data


__all__ = [
    "handle_get_pinout",
    "handle_get_pinout_targets",
    "handle_get_pinout_by_build_id",
]
