"""REST routes for DeepPCB autolayout jobs."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from atopile.server.domains.autolayout.service import get_autolayout_service

router = APIRouter(prefix="/api/autolayout", tags=["autolayout"])


class StartAutolayoutRequest(BaseModel):
    """Request payload for starting a new autolayout job."""

    model_config = ConfigDict(populate_by_name=True)

    project_root: str = Field(alias="projectRoot")
    build_target: str = Field(default="default", alias="buildTarget")
    constraints: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class StartAutolayoutResponse(BaseModel):
    """Response payload for a newly started autolayout job."""

    job: dict[str, Any]


class GetAutolayoutJobResponse(BaseModel):
    """Response payload for a single autolayout job."""

    job: dict[str, Any]


class ListAutolayoutJobsResponse(BaseModel):
    """Response payload for autolayout job history."""

    jobs: list[dict[str, Any]]


class ListAutolayoutCandidatesResponse(BaseModel):
    """Response payload for autolayout candidates."""

    candidates: list[dict[str, Any]]


@router.post("/jobs", response_model=StartAutolayoutResponse)
async def start_autolayout_job(
    request: StartAutolayoutRequest,
) -> StartAutolayoutResponse:
    """Start an autolayout job for a project/build target."""
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Project not found: {request.project_root}",
        )

    service = get_autolayout_service()
    job = await asyncio.to_thread(
        service.start_job,
        request.project_root,
        request.build_target,
        request.constraints,
        request.options,
    )
    return StartAutolayoutResponse(job=job.to_dict())


@router.get("/jobs", response_model=ListAutolayoutJobsResponse)
async def list_autolayout_jobs(
    project_root: str | None = Query(None, alias="project_root"),
) -> ListAutolayoutJobsResponse:
    """List autolayout jobs, optionally filtered by project root."""
    if project_root:
        project_path = Path(project_root)
        if not project_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Project not found: {project_root}",
            )

    service = get_autolayout_service()
    jobs = await asyncio.to_thread(service.list_jobs, project_root)
    return ListAutolayoutJobsResponse(jobs=[job.to_dict() for job in jobs])


@router.get("/jobs/{job_id}", response_model=GetAutolayoutJobResponse)
async def get_autolayout_job(
    job_id: str,
    refresh: bool = Query(True),
) -> GetAutolayoutJobResponse:
    """Get current state for an autolayout job."""
    service = get_autolayout_service()
    try:
        job = await asyncio.to_thread(
            service.refresh_job if refresh else service.get_job,
            job_id,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown autolayout job: {job_id}",
        ) from None

    return GetAutolayoutJobResponse(job=job.to_dict())


@router.get(
    "/jobs/{job_id}/candidates",
    response_model=ListAutolayoutCandidatesResponse,
)
async def list_autolayout_candidates(
    job_id: str,
    refresh: bool = Query(True),
) -> ListAutolayoutCandidatesResponse:
    """List candidates for a specific autolayout job."""
    service = get_autolayout_service()
    try:
        candidates = await asyncio.to_thread(service.list_candidates, job_id, refresh)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown autolayout job: {job_id}",
        ) from None

    return ListAutolayoutCandidatesResponse(
        candidates=[candidate.to_dict() for candidate in candidates]
    )
