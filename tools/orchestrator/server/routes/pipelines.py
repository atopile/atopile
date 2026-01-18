"""Pipeline API routes for the orchestrator server."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ...core import PipelineExecutor, PipelineStateStore
from ...models import (
    CreatePipelineRequest,
    PipelineActionResponse,
    PipelineListResponse,
    PipelineState,
    PipelineStateResponse,
    PipelineStatus,
    UpdatePipelineRequest,
)
from ..dependencies import get_pipeline_executor, get_pipeline_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.post("", response_model=PipelineState)
async def create_pipeline(
    request: CreatePipelineRequest,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
) -> PipelineState:
    """Create a new pipeline."""
    pipeline = PipelineState(
        name=request.name,
        description=request.description,
        nodes=request.nodes,
        edges=request.edges,
        config=request.config,
        status=PipelineStatus.DRAFT,
    )

    pipeline_store.set(pipeline.id, pipeline)
    logger.info(f"Created pipeline {pipeline.id}: {pipeline.name}")

    return pipeline


@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
    status: PipelineStatus | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> PipelineListResponse:
    """List all pipelines with optional filtering."""
    pipelines = pipeline_store.values()

    if status is not None:
        pipelines = [p for p in pipelines if p.status == status]

    # Sort by updated_at descending
    pipelines.sort(key=lambda p: p.updated_at, reverse=True)
    pipelines = pipelines[:limit]

    return PipelineListResponse(pipelines=pipelines, total=pipeline_store.count())


@router.get("/{pipeline_id}", response_model=PipelineState)
async def get_pipeline(
    pipeline_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
) -> PipelineState:
    """Get a specific pipeline."""
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")
    return pipeline


@router.put("/{pipeline_id}", response_model=PipelineState)
async def update_pipeline(
    pipeline_id: str,
    request: UpdatePipelineRequest,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
) -> PipelineState:
    """Update a pipeline."""
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")

    if pipeline.status == PipelineStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail="Cannot update a running pipeline. Stop it first.",
        )

    # Update fields
    if request.name is not None:
        pipeline.name = request.name
    if request.description is not None:
        pipeline.description = request.description
    if request.nodes is not None:
        pipeline.nodes = request.nodes
    if request.edges is not None:
        pipeline.edges = request.edges
    if request.config is not None:
        pipeline.config = request.config

    pipeline.touch()
    pipeline_store.set(pipeline_id, pipeline)

    logger.info(f"Updated pipeline {pipeline_id}")
    return pipeline


@router.delete("/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
) -> dict:
    """Delete a pipeline."""
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")

    if pipeline.status == PipelineStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a running pipeline. Stop it first.",
        )

    pipeline_store.delete(pipeline_id)
    logger.info(f"Deleted pipeline {pipeline_id}")

    return {"status": "deleted", "pipeline_id": pipeline_id}


@router.post("/{pipeline_id}/run", response_model=PipelineActionResponse)
async def run_pipeline(
    pipeline_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
    pipeline_executor: Annotated[PipelineExecutor, Depends(get_pipeline_executor)],
) -> PipelineActionResponse:
    """Start or resume a pipeline execution."""
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")

    if pipeline.status == PipelineStatus.RUNNING:
        return PipelineActionResponse(
            status="already_running",
            message="Pipeline is already running",
            pipeline_id=pipeline_id,
        )

    # Validate pipeline has nodes
    if not pipeline.nodes:
        raise HTTPException(
            status_code=400,
            detail="Pipeline has no nodes. Add at least a trigger and an agent.",
        )

    # Start the pipeline executor FIRST (it will set status to RUNNING internally)
    started = pipeline_executor.start_pipeline(pipeline_id)
    if not started:
        return PipelineActionResponse(
            status="failed",
            message="Failed to start pipeline execution",
            pipeline_id=pipeline_id,
        )

    logger.info(f"Started pipeline {pipeline_id}")

    return PipelineActionResponse(
        status="started",
        message="Pipeline execution started",
        pipeline_id=pipeline_id,
    )


@router.post("/{pipeline_id}/pause", response_model=PipelineActionResponse)
async def pause_pipeline(
    pipeline_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
) -> PipelineActionResponse:
    """Pause a running pipeline."""
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")

    if pipeline.status != PipelineStatus.RUNNING:
        return PipelineActionResponse(
            status="not_running",
            message=f"Pipeline is not running (status: {pipeline.status})",
            pipeline_id=pipeline_id,
        )

    # Update status
    def updater(p: PipelineState) -> PipelineState:
        p.status = PipelineStatus.PAUSED
        p.touch()
        return p

    pipeline_store.update(pipeline_id, updater)

    logger.info(f"Paused pipeline {pipeline_id}")

    return PipelineActionResponse(
        status="paused",
        message="Pipeline execution paused",
        pipeline_id=pipeline_id,
    )


@router.post("/{pipeline_id}/resume", response_model=PipelineActionResponse)
async def resume_pipeline(
    pipeline_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
) -> PipelineActionResponse:
    """Resume a paused pipeline."""
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")

    if pipeline.status != PipelineStatus.PAUSED:
        return PipelineActionResponse(
            status="not_paused",
            message=f"Pipeline is not paused (status: {pipeline.status})",
            pipeline_id=pipeline_id,
        )

    # Update status
    def updater(p: PipelineState) -> PipelineState:
        p.status = PipelineStatus.RUNNING
        p.touch()
        return p

    pipeline_store.update(pipeline_id, updater)

    logger.info(f"Resumed pipeline {pipeline_id}")

    return PipelineActionResponse(
        status="resumed",
        message="Pipeline execution resumed",
        pipeline_id=pipeline_id,
    )


@router.post("/{pipeline_id}/stop", response_model=PipelineActionResponse)
async def stop_pipeline(
    pipeline_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
) -> PipelineActionResponse:
    """Stop a running or paused pipeline."""
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")

    if pipeline.status not in (PipelineStatus.RUNNING, PipelineStatus.PAUSED):
        return PipelineActionResponse(
            status="not_running",
            message=f"Pipeline is not running or paused (status: {pipeline.status})",
            pipeline_id=pipeline_id,
        )

    # Update status
    def updater(p: PipelineState) -> PipelineState:
        p.status = PipelineStatus.COMPLETED
        p.finished_at = datetime.now()
        p.touch()
        return p

    pipeline_store.update(pipeline_id, updater)

    # TODO: Actually stop running agents

    logger.info(f"Stopped pipeline {pipeline_id}")

    return PipelineActionResponse(
        status="stopped",
        message="Pipeline execution stopped",
        pipeline_id=pipeline_id,
    )


@router.get("/{pipeline_id}/status", response_model=PipelineStateResponse)
async def get_pipeline_status(
    pipeline_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
) -> PipelineStateResponse:
    """Get the execution status of a pipeline."""
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"Pipeline not found: {pipeline_id}")

    return PipelineStateResponse(pipeline=pipeline)
