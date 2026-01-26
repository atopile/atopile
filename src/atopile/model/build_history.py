"""
Build history persistence helpers.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from atopile import sqlite_model

log = logging.getLogger(__name__)

_table: sqlite_model.TableHelper | None = None

_COLUMNS = [
    "build_id", "project_root", "target", "entry", "status",
    "return_code", "error", "started_at", "duration", "stages",
    "warnings", "errors", "completed_at",
]


def _from_row(row: sqlite3.Row):
    from atopile.dataclasses import BuildStatus, HistoricalBuild

    return HistoricalBuild(
        build_id=row["build_id"],
        project_root=row["project_root"],
        target=row["target"],
        entry=row["entry"],
        status=BuildStatus(row["status"]),
        return_code=row["return_code"],
        error=row["error"],
        started_at=row["started_at"],
        duration=row["duration"],
        stages=json.loads(row["stages"]) if row["stages"] else [],
        warnings=row["warnings"],
        errors=row["errors"],
        completed_at=row["completed_at"],
    )


def init_build_history_db(db_path: Path) -> None:
    """Initialize the build history SQLite database."""
    global _table

    try:
        _table = sqlite_model.TableHelper(
            db_path, "build_history.sql", "build_history", _COLUMNS,
            pk_columns=frozenset({"build_id"}),
            from_row=_from_row,
        )
        log.info(f"Initialized build history database: {db_path}")
    except Exception as exc:
        log.error(f"Failed to initialize build history database: {exc}")


def get_build_history_db() -> Path | None:
    """Return the current build history database path."""
    return _table._db_path if _table else None


def save_build(build) -> None:
    """Save a build record to history."""
    if _table:
        _table.save(build)


def update_build(build, *, where: str, params=()) -> int:
    """Update a build record. Returns affected row count."""
    if not _table:
        return 0
    return _table.update(build, where=where, params=params)


def load_recent_builds_from_history(limit: int = 50) -> list:
    """Load recent builds from the history database."""
    if not _table:
        return []

    try:
        return _table.query_all(order_by="started_at DESC", limit=limit)
    except Exception as exc:
        log.error(f"Failed to load build history: {exc}")
        return []


def get_build_info_by_id(build_id: str):
    """
    Get build info by build_id.

    Returns build record or None if not found.
    This provides translation from build_id -> (project, target, timestamp).
    """
    if not _table:
        return None

    try:
        return _table.query_one(where="build_id = ?", params=(build_id,))
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
    if not _table:
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
            where=where,
            params=params,
            order_by="started_at DESC",
            limit=limit,
        )
    except Exception as exc:
        log.error(f"Failed to get builds by project/target: {exc}")
        return []


def get_latest_build_for_target(
    project_root: str, target: str,
):
    """Get the most recent build for a specific project/target."""
    if not _table:
        return None

    try:
        return _table.query_one(
            where="project_root = ? AND target = ?",
            params=(project_root, target),
            order_by="started_at DESC",
        )
    except Exception as exc:
        log.error(f"Failed to get latest build for target: {exc}")
        return None
