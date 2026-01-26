"""
Build history persistence helpers.

Uses sqlite_model helpers for connection management and type-safe
schema generation / row conversion.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from atopile import sqlite_model
from atopile.dataclasses import BuildStatus, HistoricalBuild

if TYPE_CHECKING:
    from atopile.dataclasses import ActiveBuild

log = logging.getLogger(__name__)

_build_history_db: Path | None = None


def init_build_history_db(db_path: Path) -> None:
    """Initialize the build history SQLite database."""
    global _build_history_db
    _build_history_db = db_path

    try:
        sqlite_model.init_db(db_path, HistoricalBuild)
        log.info(f"Initialized build history database: {db_path}")
    except Exception as exc:
        log.error(f"Failed to initialize build history database: {exc}")


def save_build_to_history(build_id: str, build: ActiveBuild) -> None:
    """Save a build record to the history database."""
    if not _build_history_db:
        return

    try:
        stages = build.stages or []
        warnings = sum(s.get("warnings", 0) for s in stages)
        errors = sum(s.get("errors", 0) for s in stages)

        completed_at = time.time()
        started_at = build.started_at or completed_at
        duration = completed_at - started_at

        row = HistoricalBuild(
            build_id=build_id,
            project_root=build.project_root or "",
            target=build.target or "default",
            entry=build.entry,
            status=build.status,
            return_code=build.return_code,
            error=build.error,
            started_at=started_at,
            duration=duration,
            stages=stages,
            warnings=warnings,
            errors=errors,
            completed_at=completed_at,
        )

        sqlite_model.save(_build_history_db, row)
        log.debug(f"Saved build {build_id} to history")
    except Exception as exc:
        log.error(f"Failed to save build to history: {exc}")


def load_recent_builds_from_history(limit: int = 50) -> list[HistoricalBuild]:
    """Load recent builds from the history database."""
    if not _build_history_db or not _build_history_db.exists():
        return []

    try:
        return sqlite_model.query_all(
            _build_history_db,
            HistoricalBuild,
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
        return sqlite_model.query_one(
            _build_history_db,
            HistoricalBuild,
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

        return sqlite_model.query_all(
            _build_history_db,
            HistoricalBuild,
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
        return sqlite_model.query_one(
            _build_history_db,
            HistoricalBuild,
            where="project_root = ? AND target = ?",
            params=(project_root, target),
            order_by="started_at DESC",
        )
    except Exception as exc:
        log.error(f"Failed to get latest build for target: {exc}")
        return None


def update_build_status(
    build_id: str,
    status: BuildStatus,
    stages: list | None = None,
    warnings: int = 0,
    errors: int = 0,
    return_code: int | None = None,
    error: str | None = None,
) -> bool:
    """Update an existing build record in the database."""
    if not _build_history_db:
        return False

    try:
        status_value = status.value

        updates = ["status = ?", "warnings = ?", "errors = ?"]
        params: list[Any] = [status_value, warnings, errors]

        if stages is not None:
            updates.append("stages = ?")
            params.append(json.dumps(stages))
        if return_code is not None:
            updates.append("return_code = ?")
            params.append(return_code)
        if error is not None:
            updates.append("error = ?")
            params.append(error)

        finished_statuses = (
            BuildStatus.SUCCESS,
            BuildStatus.FAILED,
            BuildStatus.CANCELLED,
            BuildStatus.WARNING,
        )
        if status in finished_statuses:
            updates.append("completed_at = ?")
            params.append(time.time())

        params.append(build_id)

        rowcount = sqlite_model.execute(
            _build_history_db,
            f"UPDATE build_history SET {', '.join(updates)} WHERE build_id = ?",
            params,
        )

        if rowcount > 0:
            log.debug(f"Updated build {build_id} status to {status_value}")
        return rowcount > 0

    except Exception as exc:
        log.error(f"Failed to update build status: {exc}")
        return False


def create_build_record(
    build_id: str,
    project_root: str,
    target: str,
    entry: str | None = None,
    status: BuildStatus = BuildStatus.QUEUED,
) -> bool:
    """Create a new build record in the database."""
    if not _build_history_db:
        return False

    try:
        row = HistoricalBuild(
            build_id=build_id,
            project_root=project_root,
            target=target,
            entry=entry,
            status=status,
            started_at=time.time(),
            duration=0.0,
            stages=[],
            warnings=0,
            errors=0,
        )

        sqlite_model.save(_build_history_db, row)
        log.debug(f"Created build record {build_id} with status {status.value}")
        return True

    except Exception as exc:
        log.error(f"Failed to create build record: {exc}")
        return False
