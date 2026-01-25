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
                    "target": row["targets"],  # Column named "targets" but stores single target
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
            "target": row["targets"],  # Column named "targets" but stores single target
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
            # Column named "targets" but stores single target string
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
                    "target": row["targets"],  # Column named "targets" but stores single target
                    "project_root": row["project_root"],
                }
            )
        return builds

    except Exception as exc:
        log.error(f"Failed to get builds by project/target: {exc}")
        return []
