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

if TYPE_CHECKING:
    from atopile.dataclasses import ActiveBuild

log = logging.getLogger(__name__)

_build_history_db: Path | None = None

BUILD_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS build_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id TEXT UNIQUE NOT NULL,
    build_key TEXT NOT NULL,
    project_root TEXT NOT NULL,
    targets TEXT NOT NULL,
    entry TEXT,
    status TEXT NOT NULL,
    return_code INTEGER,
    error TEXT,
    started_at REAL NOT NULL,
    completed_at REAL,
    stages TEXT,
    warnings INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0
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

        # Get status value (enum to string)
        if hasattr(build.status, "value"):
            status_value = build.status.value
        else:
            status_value = str(build.status)

        cursor.execute(
            """
            INSERT OR REPLACE INTO build_history
            (build_id, build_key, project_root, targets, entry, status,
             return_code, error, started_at, completed_at, stages, warnings, errors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                build_id,
                "",  # build_key not stored in ActiveBuild
                build.project_root or "",
                # Store target as single value (column still named "targets" for compat)
                build.target or "default",
                build.entry,
                status_value,
                build.return_code,
                build.error,
                build.started_at or time.time(),
                time.time(),  # completed_at
                json.dumps(stages),
                warnings,
                errors,
            ),
        )
        conn.commit()
        conn.close()
        log.debug(f"Saved build {build_id} to history")
    except Exception as exc:
        log.error(f"Failed to save build to history: {exc}")


def load_recent_builds_from_history(limit: int = 50) -> list[dict]:
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

        builds = []
        for row in rows:
            builds.append(
                {
                    "build_id": row["build_id"],
                    "build_key": row["build_key"],
                    "project_root": row["project_root"],
                    "target": row["targets"],  # Column stores single target
                    "entry": row["entry"],
                    "status": row["status"],
                    "return_code": row["return_code"],
                    "error": row["error"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "stages": json.loads(row["stages"]) if row["stages"] else [],
                    "warnings": row["warnings"],
                    "errors": row["errors"],
                }
            )
        return builds

    except Exception as exc:
        log.error(f"Failed to load build history: {exc}")
        return []


def get_build_history_db() -> Path | None:
    """Return the current build history database path."""
    return _build_history_db


def get_build_info_by_id(build_id: str) -> dict | None:
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

        return {
            "build_id": row["build_id"],
            "build_key": row["build_key"],
            "project_root": row["project_root"],
            "target": row["targets"],  # Column stores single target
            "entry": row["entry"],
            "status": row["status"],
            "return_code": row["return_code"],
            "error": row["error"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "stages": json.loads(row["stages"]) if row["stages"] else [],
            "warnings": row["warnings"],
            "errors": row["errors"],
            "duration": (row["completed_at"] - row["started_at"])
            if row["completed_at"] and row["started_at"]
            else None,
        }

    except Exception as exc:
        log.error(f"Failed to get build info by id: {exc}")
        return None


def get_builds_by_project_target(
    project_root: str | None = None,
    target: str | None = None,
    limit: int = 50,
) -> list[dict]:
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
            query += " AND targets = ?"
            params.append(target)

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        builds = []
        for row in rows:
            builds.append(
                {
                    "build_id": row["build_id"],
                    "status": row["status"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "duration": (row["completed_at"] - row["started_at"])
                    if row["completed_at"] and row["started_at"]
                    else None,
                    "warnings": row["warnings"],
                    "errors": row["errors"],
                    "target": row["targets"],  # Column stores single target
                    "project_root": row["project_root"],
                }
            )
        return builds

    except Exception as exc:
        log.error(f"Failed to get builds by project/target: {exc}")
        return []


def get_latest_build_for_target(project_root: str, target: str) -> dict | None:
    """
    Get the most recent build for a specific project/target.

    Args:
        project_root: The project root path
        target: The build target name

    Returns:
        Build record dict or None if not found
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
            WHERE project_root = ? AND targets = ?
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (project_root, target),
        )

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return {
            "build_id": row["build_id"],
            "build_key": row["build_key"],
            "project_root": row["project_root"],
            "target": row["targets"],
            "entry": row["entry"],
            "status": row["status"],
            "return_code": row["return_code"],
            "error": row["error"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "stages": json.loads(row["stages"]) if row["stages"] else [],
            "warnings": row["warnings"],
            "errors": row["errors"],
            "duration": (row["completed_at"] - row["started_at"])
            if row["completed_at"] and row["started_at"]
            else None,
        }

    except Exception as exc:
        log.error(f"Failed to get latest build for target: {exc}")
        return None


def update_build_status(
    build_id: str,
    status: str,
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
        status: New status value
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

        # Build dynamic update query
        updates = ["status = ?", "warnings = ?", "errors = ?"]
        params: list = [status, warnings, errors]

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
        finished_statuses = ("success", "failed", "cancelled", "warning")
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
            log.debug(f"Updated build {build_id} status to {status}")
        return updated

    except Exception as exc:
        log.error(f"Failed to update build status: {exc}")
        return False


def create_build_record(
    build_id: str,
    project_root: str,
    target: str,
    entry: str | None = None,
    status: str = "queued",
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
        status: Initial status (default: "queued")
        timestamp: Build timestamp string (optional)

    Returns:
        True if creation succeeded, False otherwise
    """
    if not _build_history_db:
        return False

    try:
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO build_history
            (build_id, build_key, project_root, targets, entry,
             status, started_at, stages, warnings, errors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                build_id,
                timestamp or "",
                project_root,
                target,
                entry,
                status,
                time.time(),
                "[]",  # Empty stages
                0,
                0,
            ),
        )

        conn.commit()
        conn.close()
        log.debug(f"Created build record {build_id} with status {status}")
        return True

    except Exception as exc:
        log.error(f"Failed to create build record: {exc}")
        return False
