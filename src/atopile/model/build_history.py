"""
Build history persistence helpers.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import TYPE_CHECKING

from atopile.dataclasses import BuildStatus, HistoricalBuild

if TYPE_CHECKING:
    from atopile.dataclasses import ActiveBuild

log = logging.getLogger(__name__)

_build_history_db: Path | None = None


# Schema matches HistoricalBuild dataclass field order
BUILD_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS build_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- BaseBuild fields
    build_id TEXT UNIQUE NOT NULL,
    project_root TEXT NOT NULL,
    target TEXT NOT NULL,
    entry TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    return_code INTEGER,
    error TEXT,
    started_at REAL NOT NULL DEFAULT 0,
    duration REAL DEFAULT 0,
    stages TEXT DEFAULT '[]',
    warnings INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    -- HistoricalBuild fields
    completed_at REAL,
    build_key TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_build_history_project ON build_history(project_root);
CREATE INDEX IF NOT EXISTS idx_build_history_status ON build_history(status);
CREATE INDEX IF NOT EXISTS idx_build_history_started ON build_history(started_at DESC);
"""


def init_build_history_db(db_path: Path) -> None:
    """Initialize the build history SQLite database."""
    global _build_history_db
    _build_history_db = db_path

    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.executescript(BUILD_HISTORY_SCHEMA)
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

        # Get status value from BuildStatus enum
        status_value = build.status.value

        completed_at = time.time()
        started_at = build.started_at or completed_at
        duration = completed_at - started_at

        cursor.execute(
            """
            INSERT OR REPLACE INTO build_history
            (build_id, project_root, target, entry, status, return_code, error,
             started_at, duration, stages, warnings, errors, completed_at, build_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                build_id,
                build.project_root or "",
                build.target or "default",
                build.entry,
                status_value,
                build.return_code,
                build.error,
                started_at,
                duration,
                json.dumps(stages),
                warnings,
                errors,
                completed_at,
                build.timestamp,
            ),
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

        return [HistoricalBuild.from_db_row(row) for row in rows]

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

        return HistoricalBuild.from_db_row(row)

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

        return [HistoricalBuild.from_db_row(row) for row in rows]

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

        return HistoricalBuild.from_db_row(row)

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
    timestamp: str | None = None,
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
        timestamp: Build timestamp string (optional)

    Returns:
        True if creation succeeded, False otherwise
    """
    if not _build_history_db:
        return False

    try:
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        cursor = conn.cursor()

        # Get status value string from enum
        status_value = status.value

        cursor.execute(
            """
            INSERT OR REPLACE INTO build_history
            (build_id, project_root, target, entry, status, started_at,
             duration, stages, warnings, errors, build_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                build_id,
                project_root,
                target,
                entry,
                status_value,
                time.time(),
                0.0,
                "[]",
                0,
                0,
                timestamp or "",
            ),
        )

        conn.commit()
        conn.close()
        log.debug(f"Created build record {build_id} with status {status_value}")
        return True

    except Exception as exc:
        log.error(f"Failed to create build record: {exc}")
        return False
