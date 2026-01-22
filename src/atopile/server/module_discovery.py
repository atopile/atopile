"""
Module discovery wrappers.
"""

from __future__ import annotations

from pathlib import Path

from atopile.server.core import projects as core_projects


def extract_modules_from_file(ato_file: Path, project_root: Path):
    """Extract module/interface/component definitions from an .ato file."""
    return core_projects.extract_modules_from_file(ato_file, project_root)


def discover_modules_in_project(project_root: Path):
    """Discover all module definitions in a project by scanning .ato files."""
    return core_projects.discover_modules_in_project(project_root)


__all__ = ["discover_modules_in_project", "extract_modules_from_file"]
