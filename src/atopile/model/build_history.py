"""
Build history persistence helpers.

Query helpers on top of BuildHistory from model/sqlite.py.
"""

from __future__ import annotations

import logging

from atopile.model.sqlite import BuildHistory

log = logging.getLogger(__name__)


def load_recent_builds_from_history(limit: int = 50) -> list:
    """Load recent builds from the history database."""
    try:
        return BuildHistory.get_all(limit=limit)
    except Exception as exc:
        log.error(f"Failed to load build history: {exc}")
        return []


def get_build_info_by_id(build_id: str):
    """
    Get build info by build_id.

    Returns build record or None if not found.
    This provides translation from build_id -> (project, target, timestamp).
    """
    try:
        return BuildHistory.get(build_id)
    except Exception as exc:
        log.error(f"Failed to get build info by id: {exc}")
        return None


def get_builds_by_project_target(
    project_root: str | None = None,
    target: str | None = None,
    limit: int = 50,
) -> list:
    """
    Get builds by project root and/or target.

    This provides reverse lookup: (project, target) -> list of build_ids.
    """
    try:
        builds = BuildHistory.get_all(limit=limit)
        if project_root:
            builds = [b for b in builds if b.project_root == project_root]
        if target:
            builds = [b for b in builds if b.target == target]
        return builds
    except Exception as exc:
        log.error(f"Failed to get builds by project/target: {exc}")
        return []


def get_latest_build_for_target(
    project_root: str, target: str,
):
    """Get the most recent build for a specific project/target."""
    try:
        builds = BuildHistory.get_all(limit=1000)
        for b in builds:
            if b.project_root == project_root and b.target == target:
                return b
        return None
    except Exception as exc:
        log.error(f"Failed to get latest build for target: {exc}")
        return None
