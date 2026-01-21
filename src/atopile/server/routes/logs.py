"""Log-related API routes."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from atopile.server.app_context import AppContext
from atopile.server.domains import logs as logs_domain
from atopile.server.domains.deps import get_ctx

log = logging.getLogger(__name__)

router = APIRouter(tags=["logs"])


@router.get("/api/logs/{build_name}/{log_filename}")
async def get_log_file(
    build_name: str,
    log_filename: str,
    ctx: AppContext = Depends(get_ctx),
):
    """Get raw log file contents."""
    content = logs_domain.handle_get_log_file(build_name, log_filename, ctx)
    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Log file not found: {build_name}/{log_filename}",
        )
    return PlainTextResponse(content=content, media_type="text/plain")


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
    """Query logs from the central database with filters."""
    try:
        return logs_domain.handle_query_logs(
            build_name=build_name,
            project_name=project_name,
            levels=levels,
            search=search,
            after_id=after_id,
            build_id=build_id,
            project_path=project_path,
            target=target,
            stage=stage,
            level=level,
            audience=audience,
            limit=limit,
            offset=offset,
        )
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
    """Get log counts by level."""
    try:
        return logs_domain.handle_get_log_counts(
            build_name=build_name,
            project_name=project_name,
            stage=stage,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
