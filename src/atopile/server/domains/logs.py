"""Log-related API routes."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from atopile.logging import get_central_log_db
from atopile.server.app_context import AppContext
from atopile.server.domains.deps import get_ctx

log = logging.getLogger(__name__)

router = APIRouter(tags=["logs"])


@router.get("/api/logs/{build_name}/{log_filename}")
async def get_log_file(
    build_name: str,
    log_filename: str,
    ctx: AppContext = Depends(get_ctx),
):
    try:
        summary_path = ctx.summary_file
        if summary_path is None or not summary_path.exists():
            raise HTTPException(status_code=404, detail="No summary file found")

        summary = json.loads(summary_path.read_text())

        log_dir = None
        for build in summary.get("builds", []):
            if build.get("name") == build_name or build.get("display_name") == build_name:
                log_dir = build.get("log_dir")
                break

        if not log_dir:
            raise HTTPException(status_code=404, detail=f"Build not found: {build_name}")

        log_file = Path(log_dir) / log_filename
        if not log_file.exists():
            raise HTTPException(
                status_code=404, detail=f"Log file not found: {log_filename}"
            )

        return PlainTextResponse(
            content=log_file.read_text(),
            media_type="text/plain",
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/logs/query")
async def query_logs(
    build_name: Optional[str] = Query(
        None, description="Filter by build/target name (e.g., 'project:target')"
    ),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    levels: Optional[str] = Query(
        None, description="Comma-separated log levels (DEBUG,INFO,WARNING,ERROR)"
    ),
    search: Optional[str] = Query(None, description="Search in log messages"),
    after_id: Optional[int] = Query(
        None, description="Return logs after this ID (for incremental fetch)"
    ),
    build_id: Optional[str] = Query(
        None, description="Filter by build ID (from central database)"
    ),
    project_path: Optional[str] = Query(None, description="Filter by project path"),
    target: Optional[str] = Query(None, description="Filter by target name"),
    stage: Optional[str] = Query(None, description="Filter by build stage"),
    level: Optional[str] = Query(None, description="Filter by single log level"),
    audience: Optional[str] = Query(
        None, description="Filter by audience (user, developer, agent)"
    ),
    limit: int = Query(500, ge=1, le=10000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset for pagination"),
):
    try:
        central_db = get_central_log_db()
        if not central_db.exists():
            return {"logs": [], "total": 0, "max_id": 0, "has_more": False}

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
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/logs/counts")
async def get_log_counts(
    build_name: Optional[str] = Query(
        None, description="Filter by build/target name"
    ),
    project_name: Optional[str] = Query(None, description="Filter by project name"),
    stage: Optional[str] = Query(None, description="Filter by build stage"),
):
    try:
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
        raise HTTPException(status_code=500, detail=str(exc))
