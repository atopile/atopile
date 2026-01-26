"""
Build history persistence helpers.
"""

from __future__ import annotations

import logging
from pathlib import Path

from atopile import sqlite_model
from atopile.dataclasses import HistoricalBuild

log = logging.getLogger(__name__)

_build_history_db: Path | None = None

_table = sqlite_model.historical_builds


def init_build_history_db(db_path: Path) -> None:
    """Initialize the build history SQLite database."""
    global _build_history_db
    _build_history_db = db_path

    try:
        sqlite_model.init_db(db_path, "build_history.sql")
        log.info(f"Initialized build history database: {db_path}")
    except Exception as exc:
        log.error(f"Failed to initialize build history database: {exc}")


def load_recent_builds_from_history(limit: int = 50) -> list[HistoricalBuild]:
    """Load recent builds from the history database."""
    if not _build_history_db or not _build_history_db.exists():
        return []

    try:
        return _table.query_all(
            _build_history_db,
            order_by="started_at DESC",
            limit=limit,
        )
    except Exception as exc:
        log.error(f"Failed to load build history: {exc}")
        return []


def get_build_history_db() -> Path | None:
    """Return the current build history database path."""
    return _build_history_db


def get_build_info_by_id(build_id: str) -> HistoricalBuild | None:
    """
    Get build info by build_id.

    Returns build record or None if not found.
    This provides translation from build_id -> (project, target, timestamp).
    """
    if not _build_history_db or not _build_history_db.exists():
        return None

    try:
        return _table.query_one(
            _build_history_db,
            where="build_id = ?",
            params=(build_id,),
        )
    except Exception as exc:
        log.error(f"Failed to get build info by id: {exc}")
        return None


def get_builds_by_project_target(
    project_root: str | None = None,
    target: str | None = None,
    limit: int = 50,
) -> list[HistoricalBuild]:
    """
    Get builds by project root and/or target.

    This provides reverse lookup: (project, target) -> list of build_ids.
    """
    if not _build_history_db or not _build_history_db.exists():
        return []

    try:
        clauses: list[str] = []
        params: list[str] = []

        if project_root:
            clauses.append("project_root = ?")
            params.append(project_root)
        if target:
            clauses.append("target = ?")
            params.append(target)

        where = " AND ".join(clauses) if clauses else ""

        return _table.query_all(
            _build_history_db,
            where=where,
            params=params,
            order_by="started_at DESC",
            limit=limit,
        )
    except Exception as exc:
        log.error(f"Failed to get builds by project/target: {exc}")
        return []


def get_latest_build_for_target(
    project_root: str, target: str
) -> HistoricalBuild | None:
    """Get the most recent build for a specific project/target."""
    if not _build_history_db or not _build_history_db.exists():
        return None

    try:
        return _table.query_one(
            _build_history_db,
            where="project_root = ? AND target = ?",
            params=(project_root, target),
            order_by="started_at DESC",
        )
    except Exception as exc:
        log.error(f"Failed to get latest build for target: {exc}")
        return None


