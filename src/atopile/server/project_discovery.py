"""
Project discovery wrappers.
"""

from __future__ import annotations

from pathlib import Path

from atopile.server.core import projects as core_projects


def discover_projects_in_path(path: Path):
    """Discover all ato projects in the given path."""
    return core_projects.discover_projects_in_paths([path])


__all__ = ["discover_projects_in_path"]
