"""
Build-related API routes.

Endpoints:
- POST /api/build - Start a build
- GET /api/build/{build_id}/status - Get build status
- POST /api/build/{build_id}/cancel - Cancel a build
- GET /api/builds/active - Get active/queued builds
- GET /api/builds/queue - Get build queue
- GET /api/builds/history - Get build history
- GET /api/summary - Get build summary
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from ..dependencies import get_build_queue
from ..schemas.build import (
    Build,
    BuildRequest,
    BuildResponse,
    BuildStatusResponse,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["builds"])


def _get_state_builds():
    """Get builds from server state."""
    from ..server import _get_state_builds
    return _get_state_builds()


@router.post("/api/build", response_model=BuildResponse)
async def start_build(
    request: BuildRequest,
    background_tasks: BackgroundTasks,
    build_queue=Depends(get_build_queue)
):
    """
    Start a new build.

    Queues a build for the specified project and targets.
    The build runs in the background and progress can be monitored
    via WebSocket or the /api/build/{build_id}/status endpoint.
    """
    try:
        build_id = build_queue.enqueue(
            project_root=request.project_root,
            targets=request.targets,
            frozen=request.frozen,
            entry=request.entry,
        )

        return BuildResponse(
            success=True,
            message=f"Build queued successfully",
            build_id=build_id
        )
    except Exception as e:
        log.error(f"Failed to start build: {e}")
        return BuildResponse(
            success=False,
            message=str(e),
            build_id=None
        )


@router.get("/api/build/{build_id}/status", response_model=BuildStatusResponse)
async def get_build_status(build_id: str, build_queue=Depends(get_build_queue)):
    """
    Get the status of a specific build.
    """
    build = build_queue.get_build(build_id)

    if not build:
        raise HTTPException(status_code=404, detail=f"Build not found: {build_id}")

    return BuildStatusResponse(
        build_id=build_id,
        status=build.status,
        project_root=build.project_root or "",
        targets=build.targets or [],
        return_code=build.return_code,
        error=build.error
    )


@router.post("/api/build/{build_id}/cancel")
async def cancel_build(build_id: str):
    """
    Cancel a running or queued build.
    """
    from ..server import cancel_build as do_cancel

    success = do_cancel(build_id)
    if success:
        return {"success": True, "message": "Build cancelled"}
    else:
        raise HTTPException(status_code=404, detail=f"Build not found or cannot be cancelled: {build_id}")


@router.get("/api/builds/active")
async def get_active_builds(build_queue=Depends(get_build_queue)):
    """
    Get all active (running or queued) builds.
    """
    builds = build_queue.get_active_builds()
    return {"builds": builds}


@router.get("/api/builds/queue")
async def get_build_queue_endpoint(build_queue=Depends(get_build_queue)):
    """
    Get the build queue.
    """
    queue = build_queue.get_queue()
    return {"queue": queue}


@router.get("/api/builds/history")
async def get_build_history(
    limit: int = Query(50, description="Maximum number of builds to return")
):
    """
    Get build history from the database.
    """
    from ..server import load_recent_builds_from_history

    builds = load_recent_builds_from_history(limit=limit)
    return {"builds": builds, "total": len(builds)}


@router.get("/api/summary")
async def get_build_summary():
    """
    Get a summary of all builds.

    Returns recent builds with status information for UI display.
    """
    builds = _get_state_builds()

    # Calculate totals
    total_builds = len(builds)
    successful = sum(1 for b in builds if b.get("status") == "success")
    failed = sum(1 for b in builds if b.get("status") == "failed")
    warnings = sum(b.get("warnings", 0) for b in builds)
    errors = sum(b.get("errors", 0) for b in builds)

    from datetime import datetime

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "totals": {
            "builds": total_builds,
            "successful": successful,
            "failed": failed,
            "warnings": warnings,
            "errors": errors,
        },
        "builds": builds
    }
