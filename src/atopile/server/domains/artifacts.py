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


__all__ = [
    "handle_get_bom",
    "handle_get_bom_targets",
    "handle_get_variables",
    "handle_get_variables_targets",
]
