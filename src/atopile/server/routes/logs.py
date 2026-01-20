"""
Log-related API routes.

Endpoints:
- GET /api/logs/query - Query logs with filters
- GET /api/logs/counts - Get log counts by level
- GET /api/logs/{build_name}/{log_filename} - Get raw log file
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

log = logging.getLogger(__name__)

router = APIRouter(tags=["logs"])


def _get_log_db_path():
    """Get the log database path from server state."""
    from ..server import state
    logs_base = state.get("logs_base")
    if logs_base:
        return logs_base / "central.db"
    return None


def _get_logs_base():
    """Get the logs base directory from server state."""
    from ..server import state
    return state.get("logs_base")


@router.get("/api/logs/query")
async def query_logs(
    build_name: Optional[str] = Query(None, description="Filter by build name (format: project:target)"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    levels: Optional[str] = Query(None, description="Comma-separated list of log levels"),
    stage: Optional[str] = Query(None, description="Filter by stage"),
    search: Optional[str] = Query(None, description="Search in message"),
    after_id: Optional[int] = Query(None, description="Fetch logs after this ID (for incremental updates)"),
    limit: int = Query(500, description="Maximum number of logs to return"),
):
    """
    Query logs from the central database with filters.

    Server-side filtering reduces data transfer and improves performance.
    """
    db_path = _get_log_db_path()

    if not db_path or not db_path.exists():
        return {"logs": [], "total": 0, "has_more": False, "max_id": 0}

    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build WHERE clause
        conditions = []
        params: list = []

        if build_name:
            if ":" in build_name:
                project_part, target_part = build_name.split(":", 1)
                conditions.append("builds.target = ?")
                params.append(target_part)
                conditions.append("builds.project_path LIKE ?")
                params.append(f"%/{project_part}")
            else:
                conditions.append("builds.target = ?")
                params.append(build_name)

        if project_name:
            conditions.append("builds.project_path LIKE ?")
            params.append(f"%/{project_name}")

        if levels:
            level_list = [lv.strip().upper() for lv in levels.split(",")]
            placeholders = ",".join("?" * len(level_list))
            conditions.append(f"logs.level IN ({placeholders})")
            params.extend(level_list)

        if stage:
            conditions.append("logs.stage = ?")
            params.append(stage)

        if search:
            conditions.append("logs.message LIKE ?")
            params.append(f"%{search}%")

        if after_id:
            conditions.append("logs.id > ?")
            params.append(after_id)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Query with limit
        query = f"""
            SELECT logs.id, logs.build_id, logs.timestamp, logs.stage,
                   logs.level, logs.audience, logs.message,
                   logs.ato_traceback, logs.python_traceback,
                   builds.project_path, builds.target
            FROM logs
            JOIN builds ON logs.build_id = builds.build_id
            {where_clause}
            ORDER BY logs.id DESC
            LIMIT ?
        """
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Get total count
        count_query = f"""
            SELECT COUNT(*) FROM logs
            JOIN builds ON logs.build_id = builds.build_id
            {where_clause}
        """
        cursor.execute(count_query, params[:-1])  # Remove limit param
        total = cursor.fetchone()[0]

        # Get max ID for incremental updates
        max_id = max((row["id"] for row in rows), default=0)

        conn.close()

        # Convert to response format
        logs = [
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "stage": row["stage"],
                "level": row["level"],
                "level_no": {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "ALERT": 50}.get(row["level"], 20),
                "audience": row["audience"],
                "message": row["message"],
                "ato_traceback": row["ato_traceback"],
                "python_traceback": row["python_traceback"],
                "build_dir": row["project_path"],
            }
            for row in rows
        ]

        return {
            "logs": logs,
            "total": total,
            "has_more": total > len(logs),
            "max_id": max_id,
        }

    except Exception as e:
        log.error(f"Failed to query logs: {e}")
        return {"logs": [], "total": 0, "has_more": False, "max_id": 0, "error": str(e)}


@router.get("/api/logs/counts")
async def get_log_counts(
    build_name: Optional[str] = Query(None, description="Filter by build name"),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    stage: Optional[str] = Query(None, description="Filter by stage"),
):
    """
    Get log counts by level for badge display.

    More efficient than fetching all logs.
    """
    db_path = _get_log_db_path()

    if not db_path or not db_path.exists():
        return {
            "counts": {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "ALERT": 0},
            "total": 0
        }

    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        cursor = conn.cursor()

        # Build WHERE clause
        conditions = []
        params: list = []

        if build_name:
            if ":" in build_name:
                project_part, target_part = build_name.split(":", 1)
                conditions.append("builds.target = ?")
                params.append(target_part)
                conditions.append("builds.project_path LIKE ?")
                params.append(f"%/{project_part}")
            else:
                conditions.append("builds.target = ?")
                params.append(build_name)

        if project_name:
            conditions.append("builds.project_path LIKE ?")
            params.append(f"%/{project_name}")

        if stage:
            conditions.append("logs.stage = ?")
            params.append(stage)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT logs.level, COUNT(*) as count
            FROM logs
            JOIN builds ON logs.build_id = builds.build_id
            {where_clause}
            GROUP BY logs.level
        """

        cursor.execute(query, params)
        rows = cursor.fetchall()

        conn.close()

        counts = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "ALERT": 0}
        for level, count in rows:
            if level in counts:
                counts[level] = count

        total = sum(counts.values())

        return {"counts": counts, "total": total}

    except Exception as e:
        log.error(f"Failed to get log counts: {e}")
        return {
            "counts": {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "ALERT": 0},
            "total": 0,
            "error": str(e)
        }


@router.get("/api/logs/{build_name}/{log_filename}", response_class=PlainTextResponse)
async def get_raw_log_file(build_name: str, log_filename: str):
    """
    Get raw log file contents.
    """
    logs_base = _get_logs_base()

    if not logs_base:
        raise HTTPException(status_code=404, detail="Logs base not configured")

    log_path = logs_base / build_name / log_filename

    if not log_path.exists():
        raise HTTPException(status_code=404, detail=f"Log file not found: {log_path}")

    return log_path.read_text()
