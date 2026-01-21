"""Build-related API routes."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from atopile.server.app_context import AppContext
from atopile.server.domains import builds as builds_domain
from atopile.server.domains.deps import get_ctx
from atopile.server.schemas.build import (
    BuildRequest,
    BuildResponse,
    BuildStatusResponse,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["builds"])


@router.get("/api/summary")
async def get_summary(ctx: AppContext = Depends(get_ctx)):
    """Get build summary including active builds and build history."""
    # Run in thread pool to avoid blocking the event loop
    return await asyncio.to_thread(builds_domain.handle_get_summary, ctx)


@router.post("/api/build", response_model=BuildResponse)
async def start_build(request: BuildRequest):
    """Start a new build."""
    # Run in thread pool to avoid blocking the event loop
    response = await asyncio.to_thread(builds_domain.handle_start_build, request)
    if not response.success and response.build_id is None:
        raise HTTPException(status_code=400, detail=response.message)
    return response


@router.get("/api/build/{build_id}/status", response_model=BuildStatusResponse)
async def get_build_status(build_id: str):
    """Get the status of a specific build."""
    result = builds_domain.handle_get_build_status(build_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Build not found: {build_id}")
    return result


@router.post("/api/build/{build_id}/cancel")
async def cancel_build(build_id: str):
    """Cancel a running or queued build."""
    result = builds_domain.handle_cancel_build(build_id)
    if not result["success"] and "not found" in result["message"].lower():
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.get("/api/builds/active")
async def get_active_builds():
    """Get all active (running or queued) builds."""
    return builds_domain.handle_get_active_builds()


@router.get("/api/builds/queue")
async def get_build_queue_status():
    """Get the build queue status."""
    return builds_domain.handle_get_build_queue_status()


@router.get("/api/settings/max-concurrent")
async def get_max_concurrent_setting():
    """Get max concurrent builds setting."""
    return builds_domain.handle_get_max_concurrent_setting()


@router.post("/api/settings/max-concurrent")
async def set_max_concurrent_setting(request: builds_domain.MaxConcurrentRequest):
    """Set max concurrent builds setting."""
    return builds_domain.handle_set_max_concurrent_setting(request)


@router.get("/api/builds/history")
async def get_build_history(
    project_root: Optional[str] = Query(None, description="Filter by project root"),
    status: Optional[str] = Query(
        None, description="Filter by status (success, failed, cancelled)"
    ),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
):
    """Get build history from the database."""
    # Run in thread pool to avoid blocking the event loop (DB operations)
    return await asyncio.to_thread(
        builds_domain.handle_get_build_history, project_root, status, limit
    )
