"""Log domain logic - business logic for log operations."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

from atopile.logging import get_central_log_db
from atopile.server.app_context import AppContext

log = logging.getLogger(__name__)


def handle_get_log_file(
    build_name: str,
    log_filename: str,
    ctx: AppContext,
) -> str | None:
    """
    Get raw log file contents.

    Returns file contents as string, or None if not found.
    """
    summary_path = ctx.summary_file
    if summary_path is None or not summary_path.exists():
        return None

    try:
        summary = json.loads(summary_path.read_text())
    except Exception:
        return None

    log_dir = None
    for build in summary.get("builds", []):
        if (
            build.get("name") == build_name
            or build.get("display_name") == build_name
        ):
            log_dir = build.get("log_dir")
            break

    if not log_dir:
        return None

    log_file = Path(log_dir) / log_filename
    if not log_file.exists():
        return None

    return log_file.read_text()


def handle_query_logs(
    build_name: Optional[str] = None,
    project_name: Optional[str] = None,
    levels: Optional[str] = None,
    search: Optional[str] = None,
    after_id: Optional[int] = None,
    build_id: Optional[str] = None,
    project_path: Optional[str] = None,
    target: Optional[str] = None,
    stage: Optional[str] = None,
    level: Optional[str] = None,
    audience: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
) -> dict:
    """Query logs from the central database with filters."""
    central_db = get_central_log_db()
    if not central_db.exists():
        return {"logs": [], "total": 0, "max_id": 0, "has_more": False}

    try:
        conn = sqlite3.connect(str(central_db), timeout=5.0)
        conn.row_factory = sqlite3.Row

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

        if build_id:
            conditions.append("logs.build_id = ?")
            params.append(build_id)
        if project_path:
            conditions.append("builds.project_path = ?")
            params.append(project_path)
        if target:
            conditions.append("builds.target = ?")
            params.append(target)
        if stage:
            conditions.append("logs.stage = ?")
            params.append(stage)

        if levels:
            level_list = [lv.strip().upper() for lv in levels.split(",")]
            placeholders = ",".join("?" * len(level_list))
            conditions.append(f"logs.level IN ({placeholders})")
            params.extend(level_list)
        elif level:
            conditions.append("logs.level = ?")
            params.append(level.upper())

        if audience:
            conditions.append("logs.audience = ?")
            params.append(audience.lower())

        if search:
            conditions.append("logs.message LIKE ?")
            params.append(f"%{search}%")

        if after_id is not None:
            conditions.append("logs.id > ?")
            params.append(after_id)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        order = "ASC" if after_id is not None else "DESC"
        query = f"""
            SELECT logs.id, logs.build_id, logs.timestamp, logs.stage,
                   logs.level, logs.audience, logs.message,
                   logs.ato_traceback, logs.python_traceback,
                   builds.project_path, builds.target
            FROM logs
            JOIN builds ON logs.build_id = builds.build_id
            {where_clause}
            ORDER BY logs.id {order}
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()

        all_logs: list[dict] = []
        max_id = 0
        for row in rows:
            log_id = row["id"]
            if log_id > max_id:
                max_id = log_id
            all_logs.append(
                {
                    "id": log_id,
                    "build_id": row["build_id"],
                    "timestamp": row["timestamp"],
                    "stage": row["stage"],
                    "level": row["level"],
                    "audience": row["audience"],
                    "message": row["message"],
                    "ato_traceback": row["ato_traceback"],
                    "python_traceback": row["python_traceback"],
                    "project_path": row["project_path"],
                    "target": row["target"],
                }
            )

        count_params = params[:-2] if len(params) >= 2 else []
        count_query = f"""
            SELECT COUNT(*) as total
            FROM logs
            JOIN builds ON logs.build_id = builds.build_id
            {where_clause}
        """
        total = conn.execute(count_query, count_params).fetchone()["total"]
        has_more = len(all_logs) == limit and total > len(all_logs) + offset

        conn.close()
        return {
            "logs": all_logs,
            "total": total,
            "max_id": max_id,
            "has_more": has_more,
        }

    except sqlite3.Error as exc:
        log.warning(f"Error reading logs from central database: {exc}")
        return {"logs": [], "total": 0, "max_id": 0, "has_more": False}
    except Exception as exc:
        log.error(f"Error querying logs: {exc}")
        raise


def handle_get_log_counts(
    build_name: Optional[str] = None,
    project_name: Optional[str] = None,
    stage: Optional[str] = None,
) -> dict:
    """Get log counts by level."""
    central_db = get_central_log_db()
    if not central_db.exists():
        return {
            "counts": {
                "DEBUG": 0,
                "INFO": 0,
                "WARNING": 0,
                "ERROR": 0,
                "ALERT": 0,
            },
            "total": 0,
        }

    try:
        conn = sqlite3.connect(str(central_db), timeout=5.0)
        conn.row_factory = sqlite3.Row

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

        rows = conn.execute(query, params).fetchall()

        counts = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "ALERT": 0}
        total = 0
        for row in rows:
            level = row["level"].upper()
            count = row["count"]
            if level in counts:
                counts[level] = count
            total += count

        conn.close()
        return {"counts": counts, "total": total}

    except sqlite3.Error as exc:
        log.warning(f"Error getting log counts: {exc}")
        return {
            "counts": {
                "DEBUG": 0,
                "INFO": 0,
                "WARNING": 0,
                "ERROR": 0,
                "ALERT": 0,
            },
            "total": 0,
        }
    except Exception as exc:
        log.error(f"Error getting log counts: {exc}")
        raise


__all__ = [
    "handle_get_log_file",
    "handle_query_logs",
    "handle_get_log_counts",
]
