"""Artifact domain logic - business logic for BOM and variables."""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def handle_get_bom(project_root: str, target: str = "default") -> dict | None:
    """
    Get the bill of materials for a build target.

    Returns BOM data or None if not found.
    Raises ValueError for invalid project path.
    """
    project_path = Path(project_root)
    if not project_path.exists():
        raise ValueError(f"Project path does not exist: {project_root}")

    if not (project_path / "ato.yaml").exists():
        raise ValueError(f"No ato.yaml found in: {project_root}")

    bom_path = project_path / "build" / "builds" / target / f"{target}.bom.json"

    if not bom_path.exists():
        return None

    try:
        return json.loads(bom_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in BOM: {exc}")


def handle_get_bom_targets(project_root: str) -> dict:
    """Get available targets that have BOM data."""
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
        bom_path = target_dir / f"{target_dir.name}.bom.json"
        if bom_path.exists():
            targets.append(target_dir.name)

    return {"targets": targets, "project_root": project_root}


def handle_get_variables(project_root: str, target: str = "default") -> dict | None:
    """
    Get design variables for a build target.

    Returns variables data or None if not found.
    Raises ValueError for invalid project path.
    """
    project_path = Path(project_root)
    if not project_path.exists():
        raise ValueError(f"Project path does not exist: {project_root}")

    if not (project_path / "ato.yaml").exists():
        raise ValueError(f"No ato.yaml found in: {project_root}")

    variables_path = (
        project_path / "build" / "builds" / target / f"{target}.variables.json"
    )

    if not variables_path.exists():
        return None

    try:
        return json.loads(variables_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in variables: {exc}")


def handle_get_variables_targets(project_root: str) -> dict:
    """Get available targets that have variables data."""
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
        variables_path = target_dir / f"{target_dir.name}.variables.json"
        if variables_path.exists():
            targets.append(target_dir.name)

    return {"targets": targets, "project_root": project_root}


def handle_get_bom_by_build_id(build_id: str) -> dict | None:
    """
    Get the BOM for a specific build by build_id.

    Looks up build info, then reads the BOM artifact file.
    Verifies that the embedded build_id matches (sanity check).

    Returns BOM data or None if not found.
    """
    from atopile.model import build_history

    # Look up build info
    build_info = build_history.get_build_info_by_id(build_id)
    if not build_info:
        return None

    project_root = build_info.get("project_root")
    target = build_info.get("target")

    if not project_root or not target:
        return None

    project_path = Path(project_root)
    bom_path = project_path / "build" / "builds" / target / f"{target}.bom.json"

    if not bom_path.exists():
        return None

    try:
        data = json.loads(bom_path.read_text())
        # Verify embedded build_id matches (optional sanity check)
        embedded_build_id = data.get("build_id")
        if embedded_build_id and embedded_build_id != build_id:
            log.warning(
                f"BOM build_id mismatch: expected {build_id}, got {embedded_build_id}"
            )
        return data
    except json.JSONDecodeError as exc:
        log.error(f"Invalid JSON in BOM {bom_path}: {exc}")
        return None


def handle_get_variables_by_build_id(build_id: str) -> dict | None:
    """
    Get the variables for a specific build by build_id.

    Looks up build info, then reads the variables artifact file.
    Verifies that the embedded build_id matches (sanity check).

    Returns variables data or None if not found.
    """
    from atopile.model import build_history

    # Look up build info
    build_info = build_history.get_build_info_by_id(build_id)
    if not build_info:
        return None

    project_root = build_info.get("project_root")
    target = build_info.get("target")

    if not project_root or not target:
        return None

    project_path = Path(project_root)
    variables_path = (
        project_path / "build" / "builds" / target / f"{target}.variables.json"
    )

    if not variables_path.exists():
        return None

    try:
        data = json.loads(variables_path.read_text())
        # Verify embedded build_id matches (optional sanity check)
        embedded_build_id = data.get("build_id")
        if embedded_build_id and embedded_build_id != build_id:
            log.warning(
                f"Variables build_id mismatch: expected {build_id}, "
                f"got {embedded_build_id}"
            )
        return data
    except json.JSONDecodeError as exc:
        log.error(f"Invalid JSON in variables {variables_path}: {exc}")
        return None


__all__ = [
    "handle_get_bom",
    "handle_get_bom_targets",
    "handle_get_variables",
    "handle_get_variables_targets",
    "handle_get_bom_by_build_id",
    "handle_get_variables_by_build_id",
]
