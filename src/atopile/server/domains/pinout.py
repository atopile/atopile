"""Pinout domain logic - reads pinout JSON build artifacts."""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def handle_get_pinout(project_root: str, target: str = "default") -> dict | None:
    """
    Get pinout data for a build target.

    Returns pinout data or None if not found.
    Raises ValueError for invalid project path.
    """
    project_path = Path(project_root)
    if not project_path.exists():
        raise ValueError(f"Project path does not exist: {project_root}")

    if not (project_path / "ato.yaml").exists():
        raise ValueError(f"No ato.yaml found in: {project_root}")

    pinout_path = project_path / "build" / "builds" / target / f"{target}.pinout.json"

    if not pinout_path.exists():
        return None

    try:
        return json.loads(pinout_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in pinout: {exc}")


def handle_get_pinout_targets(project_root: str) -> dict:
    """Get available targets that have pinout data."""
    project_path = Path(project_root)
    if not project_path.exists():
        raise ValueError(f"Project path does not exist: {project_root}")

    builds_dir = project_path / "build" / "builds"
    if not builds_dir.exists():
        return {"targets": [], "project_root": project_root}

    targets = []
    for target_dir in builds_dir.iterdir():
        if not target_dir.is_dir():
            continue
        pinout_path = target_dir / f"{target_dir.name}.pinout.json"
        if pinout_path.exists():
            targets.append(target_dir.name)

    return {"targets": targets, "project_root": project_root}


def handle_get_pinout_by_build_id(build_id: str) -> dict | None:
    """
    Get the pinout for a specific build by build_id.

    Looks up build info, then reads the pinout artifact file.
    """
    from atopile.model.sqlite import BuildHistory

    build_info = BuildHistory.get(build_id)
    if not build_info:
        return None

    project_root = build_info.get("project_root")
    target = build_info.get("target")

    if not project_root or not target:
        return None

    project_path = Path(project_root)
    pinout_path = project_path / "build" / "builds" / target / f"{target}.pinout.json"

    if not pinout_path.exists():
        return None

    try:
        data = json.loads(pinout_path.read_text())
        embedded_build_id = data.get("build_id")
        if embedded_build_id and embedded_build_id != build_id:
            log.warning(
                f"Pinout build_id mismatch: expected {build_id}, "
                f"got {embedded_build_id}"
            )
        return data
    except json.JSONDecodeError as exc:
        log.error(f"Invalid JSON in pinout {pinout_path}: {exc}")
        return None


__all__ = [
    "handle_get_pinout",
    "handle_get_pinout_targets",
    "handle_get_pinout_by_build_id",
]
