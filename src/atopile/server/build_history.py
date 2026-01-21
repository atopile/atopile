"""
Build history persistence helpers.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path

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


def save_build_to_history(build_id: str, build_info: dict) -> None:
    """Save a build record to the history database."""
    if not _build_history_db:
        return

    try:
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        cursor = conn.cursor()

        # Count warnings/errors from stages
        stages = build_info.get("stages", [])
        warnings = sum(s.get("warnings", 0) for s in stages)
        errors = sum(s.get("errors", 0) for s in stages)

        cursor.execute(
            """
            INSERT OR REPLACE INTO build_history
            (build_id, build_key, project_root, targets, entry, status,
             return_code, error, started_at, completed_at, stages, warnings, errors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                build_id,
                build_info.get("build_key", ""),
                build_info.get("project_root", ""),
                json.dumps(build_info.get("targets", [])),
                build_info.get("entry"),
                build_info.get("status", "unknown"),
                build_info.get("return_code"),
                build_info.get("error"),
                build_info.get("started_at", time.time()),
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
                    "targets": json.loads(row["targets"]),
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
