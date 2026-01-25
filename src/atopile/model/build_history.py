"""
Build history persistence helpers.

Uses Pydantic models from dataclasses.py for type-safe schema generation
and row conversion.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import TYPE_CHECKING

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
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.executescript(sqlite_model.create_table_sql(HistoricalBuild))
        conn.commit()
        conn.close()
        log.info(f"Initialized build history database: {db_path}")
    except Exception as exc:
        log.error(f"Failed to initialize build history database: {exc}")


def save_build_to_history(build_id: str, build: ActiveBuild) -> None:
    """Save a build record to the history database."""
    if not _build_history_db:
        return

    try:
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        cursor = conn.cursor()

        # Count warnings/errors from stages
        stages = build.stages or []
        warnings = sum(s.get("warnings", 0) for s in stages)
        errors = sum(s.get("errors", 0) for s in stages)

        completed_at = time.time()
        started_at = build.started_at or completed_at
        duration = completed_at - started_at

        # Create a typed model for insertion
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

        # Use model's insert method - exclude 'id' for auto-increment
        columns = sqlite_model.insert_columns(HistoricalBuild, exclude={"id"})
        cursor.execute(
            sqlite_model.insert_or_replace_sql(HistoricalBuild, columns),
            sqlite_model.to_row_tuple(row, columns),
        )
        conn.commit()
        conn.close()
        log.debug(f"Saved build {build_id} to history")
    except Exception as exc:
        log.error(f"Failed to save build to history: {exc}")


def load_recent_builds_from_history(limit: int = 50) -> list[HistoricalBuild]:
    """Load recent builds from the history database."""
    if not _build_history_db or not _build_history_db.exists():
        return []

    try:
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM build_history
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        # Use type-safe Pydantic model for parsing
        return [sqlite_model.from_row(HistoricalBuild, row) for row in rows]

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
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM build_history
            WHERE build_id = ?
            """,
            (build_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        # Use type-safe Pydantic model for parsing
        return sqlite_model.from_row(HistoricalBuild, row)

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

    Args:
        project_root: Filter by project root path
        target: Filter by target name
        limit: Maximum number of results
    """
    if not _build_history_db or not _build_history_db.exists():
        return []

    try:
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query with optional filters
        query = "SELECT * FROM build_history WHERE 1=1"
        params: list = []

        if project_root:
            query += " AND project_root = ?"
            params.append(project_root)

        if target:
            # Column stores single target string
            query += " AND target = ?"
            params.append(target)

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # Use type-safe Pydantic model for parsing
        return [sqlite_model.from_row(HistoricalBuild, row) for row in rows]

    except Exception as exc:
        log.error(f"Failed to get builds by project/target: {exc}")
        return []


def get_latest_build_for_target(
    project_root: str, target: str
) -> HistoricalBuild | None:
    """
    Get the most recent build for a specific project/target.

    Args:
        project_root: The project root path
        target: The build target name

    Returns:
        HistoricalBuild object or None if not found
    """
    if not _build_history_db or not _build_history_db.exists():
        return None

    try:
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM build_history
            WHERE project_root = ? AND target = ?
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (project_root, target),
        )

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        # Use type-safe Pydantic model for parsing
        return sqlite_model.from_row(HistoricalBuild, row)

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
    """
    Update an existing build record in the database.

    This is used for live updates during build execution.

    Args:
        build_id: The build ID to update
        status: New status value (BuildStatus enum)
        stages: Optional list of stage data
        warnings: Warning count
        errors: Error count
        return_code: Exit code (if build is complete)
        error: Error message (if build failed)

    Returns:
        True if update succeeded, False otherwise
    """
    if not _build_history_db:
        return False

    try:
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        cursor = conn.cursor()

        # Get status value string from enum
        status_value = status.value

        # Build dynamic update query
        updates = ["status = ?", "warnings = ?", "errors = ?"]
        params: list = [status_value, warnings, errors]

        if stages is not None:
            updates.append("stages = ?")
            params.append(json.dumps(stages))

        if return_code is not None:
            updates.append("return_code = ?")
            params.append(return_code)

        if error is not None:
            updates.append("error = ?")
            params.append(error)

        # Update completed_at if build is finished
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

        cursor.execute(
            f"""
            UPDATE build_history
            SET {", ".join(updates)}
            WHERE build_id = ?
            """,
            params,
        )

        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()

        if updated:
            log.debug(f"Updated build {build_id} status to {status_value}")
        return updated

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
    """
    Create a new build record in the database.

    This is called at the start of a build to register it in the DB.

    Args:
        build_id: Unique build identifier
        project_root: Path to project root
        target: Build target name
        entry: Entry point (optional)
        status: Initial status (default: BuildStatus.QUEUED)
    Returns:
        True if creation succeeded, False otherwise
    """
    if not _build_history_db:
        return False

    try:
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        cursor = conn.cursor()

        # Create a typed row model for insertion
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

        # Use model's insert method - exclude 'id' for auto-increment
        columns = sqlite_model.insert_columns(HistoricalBuild, exclude={"id"})
        cursor.execute(
            sqlite_model.insert_or_replace_sql(HistoricalBuild, columns),
            sqlite_model.to_row_tuple(row, columns),
        )

        conn.commit()
        conn.close()
        log.debug(f"Created build record {build_id} with status {status.value}")
        return True

    except Exception as exc:
        log.error(f"Failed to create build record: {exc}")
        return False
