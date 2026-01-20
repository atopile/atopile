"""Pipeline API routes for the orchestrator server."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ...core import PipelineExecutor, PipelineSessionStore, PipelineStateStore
from ...models import (
    CreatePipelineRequest,
    PipelineActionResponse,
    PipelineListResponse,
    PipelineSession,
    PipelineSessionListResponse,
    PipelineSessionResponse,
    PipelineState,
    PipelineStateResponse,
    PipelineStatus,
    UpdatePipelineRequest,
)
from ..dependencies import (
    get_pipeline_executor,
    get_pipeline_session_store,
    get_pipeline_store,
)

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
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )
    return pipeline


@router.put("/{pipeline_id}", response_model=PipelineState)
async def update_pipeline(
    pipeline_id: str,
    request: UpdatePipelineRequest,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
    session_store: Annotated[PipelineSessionStore, Depends(get_pipeline_session_store)],
) -> PipelineState:
    """Update a pipeline."""
    from ...models import PipelineSessionStatus

    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    # Check for running sessions (sessions track execution state, not pipeline.status)
    sessions = session_store.get_sessions_for_pipeline(pipeline_id)
    running_sessions = [
        s for s in sessions if s.status == PipelineSessionStatus.RUNNING
    ]

    if running_sessions:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update pipeline with {len(running_sessions)} running session(s). Stop them first.",
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
    session_store: Annotated[PipelineSessionStore, Depends(get_pipeline_session_store)],
) -> dict:
    """Delete a pipeline."""
    from ...models import PipelineSessionStatus

    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    # Check for running sessions (sessions track execution state, not pipeline.status)
    sessions = session_store.get_sessions_for_pipeline(pipeline_id)
    running_sessions = [
        s for s in sessions if s.status == PipelineSessionStatus.RUNNING
    ]

    if running_sessions:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete pipeline with {len(running_sessions)} running session(s). Stop them first.",
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
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    # Note: We allow multiple sessions to run concurrently
    # Each run creates a new session

    # Validate pipeline has nodes
    if not pipeline.nodes:
        raise HTTPException(
            status_code=400,
            detail="Pipeline has no nodes. Add at least a trigger and an agent.",
        )

    # Start the pipeline executor FIRST (it will set status to RUNNING internally)
    # Returns the session ID if started successfully
    session_id = pipeline_executor.start_pipeline(pipeline_id)
    if not session_id:
        return PipelineActionResponse(
            status="failed",
            message="Failed to start pipeline execution",
            pipeline_id=pipeline_id,
        )

    logger.info(f"Started pipeline {pipeline_id} with session {session_id}")

    return PipelineActionResponse(
        status="started",
        message=f"Pipeline execution started (session: {session_id})",
        pipeline_id=pipeline_id,
    )


@router.post("/{pipeline_id}/pause", response_model=PipelineActionResponse)
async def pause_pipeline(
    pipeline_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
) -> PipelineActionResponse:
    """Pause a running pipeline - deprecated, use session-level operations."""
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    # Pipeline-level pause is deprecated - sessions manage execution state
    return PipelineActionResponse(
        status="deprecated",
        message="Pipeline-level pause is deprecated. Use session-level stop instead.",
        pipeline_id=pipeline_id,
    )


@router.post("/{pipeline_id}/resume", response_model=PipelineActionResponse)
async def resume_pipeline(
    pipeline_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
) -> PipelineActionResponse:
    """Resume a paused pipeline - deprecated, use Run to start a new session."""
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    # Pipeline-level resume is deprecated - use Run to start a new session
    return PipelineActionResponse(
        status="deprecated",
        message="Pipeline-level resume is deprecated. Use Run to start a new session.",
        pipeline_id=pipeline_id,
    )


@router.post("/{pipeline_id}/stop", response_model=PipelineActionResponse)
async def stop_pipeline(
    pipeline_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
    session_store: Annotated[PipelineSessionStore, Depends(get_pipeline_session_store)],
    pipeline_executor: Annotated[PipelineExecutor, Depends(get_pipeline_executor)],
) -> PipelineActionResponse:
    """Stop all running sessions of a pipeline."""
    import os
    import signal
    from ...models import AgentStatus, PipelineSessionStatus

    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    # Get all running sessions for this pipeline
    sessions = session_store.get_sessions_for_pipeline(pipeline_id)
    running_sessions = [
        s for s in sessions if s.status == PipelineSessionStatus.RUNNING
    ]

    if not running_sessions:
        return PipelineActionResponse(
            status="not_running",
            message="No running sessions for this pipeline",
            pipeline_id=pipeline_id,
        )

    # Stop the executor (signals background thread to stop)
    pipeline_executor.stop_pipeline(pipeline_id)

    # Terminate all agents in running sessions
    terminated_agents = []
    agent_store = pipeline_executor._agent_store
    process_manager = pipeline_executor._process_manager

    for session in running_sessions:
        for agent_id in session.node_agent_map.values():
            agent = agent_store.get(agent_id)
            if agent and agent.is_running():
                try:
                    process_manager.kill(agent_id)
                    terminated_agents.append(agent_id)
                except Exception as e:
                    logger.warning(f"Failed to terminate agent {agent_id}: {e}")
                    # Try force kill by PID
                    if agent.pid:
                        try:
                            os.kill(agent.pid, signal.SIGKILL)
                            terminated_agents.append(agent_id)
                        except Exception:
                            pass

                # Update agent state
                def make_updater():
                    def updater(a):
                        a.status = AgentStatus.TERMINATED
                        a.finished_at = datetime.now()
                        return a

                    return updater

                agent_store.update(agent_id, make_updater())

        # Update session status
        def session_updater(s: PipelineSession) -> PipelineSession:
            s.status = PipelineSessionStatus.STOPPED
            s.finished_at = datetime.now()
            return s

        session_store.update(session.id, session_updater)

    logger.info(
        f"Stopped {len(running_sessions)} sessions of pipeline {pipeline_id}, terminated {len(terminated_agents)} agents"
    )

    return PipelineActionResponse(
        status="stopped",
        message=f"Stopped {len(running_sessions)} sessions ({len(terminated_agents)} agents terminated)",
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
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    return PipelineStateResponse(pipeline=pipeline)


# Session endpoints


@router.get("/{pipeline_id}/sessions", response_model=PipelineSessionListResponse)
async def list_pipeline_sessions(
    pipeline_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
    session_store: Annotated[PipelineSessionStore, Depends(get_pipeline_session_store)],
    limit: int = Query(default=100, ge=1, le=1000),
) -> PipelineSessionListResponse:
    """List all sessions for a pipeline."""
    # Verify pipeline exists
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    sessions = session_store.get_sessions_for_pipeline(pipeline_id)

    # Sort by started_at descending (most recent first)
    sessions.sort(key=lambda s: s.started_at, reverse=True)
    sessions = sessions[:limit]

    return PipelineSessionListResponse(sessions=sessions, total=len(sessions))


@router.get(
    "/{pipeline_id}/sessions/{session_id}", response_model=PipelineSessionResponse
)
async def get_pipeline_session(
    pipeline_id: str,
    session_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
    session_store: Annotated[PipelineSessionStore, Depends(get_pipeline_session_store)],
) -> PipelineSessionResponse:
    """Get a specific pipeline session."""
    # Verify pipeline exists
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    if session.pipeline_id != pipeline_id:
        raise HTTPException(
            status_code=400,
            detail=f"Session {session_id} does not belong to pipeline {pipeline_id}",
        )

    return PipelineSessionResponse(session=session)


@router.post(
    "/{pipeline_id}/sessions/{session_id}/stop", response_model=PipelineActionResponse
)
async def stop_pipeline_session(
    pipeline_id: str,
    session_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
    session_store: Annotated[PipelineSessionStore, Depends(get_pipeline_session_store)],
    pipeline_executor: Annotated[PipelineExecutor, Depends(get_pipeline_executor)],
    force: bool = Query(
        default=False, description="Force kill agents by PID if needed"
    ),
) -> PipelineActionResponse:
    """Stop a specific pipeline session and terminate its agents."""
    import os
    import signal
    from ...models import AgentStatus, PipelineSessionStatus

    # Verify pipeline exists
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    if session.pipeline_id != pipeline_id:
        raise HTTPException(
            status_code=400,
            detail=f"Session {session_id} does not belong to pipeline {pipeline_id}",
        )

    if session.is_finished():
        return PipelineActionResponse(
            status="already_stopped",
            message=f"Session already finished with status: {session.status}",
            pipeline_id=pipeline_id,
        )

    # Terminate all agents in this session
    terminated_agents = []
    agent_store = pipeline_executor._agent_store
    process_manager = pipeline_executor._process_manager

    for agent_id in session.node_agent_map.values():
        agent = agent_store.get(agent_id)
        if agent is None:
            continue

        if agent.is_running():
            try:
                if force:
                    process_manager.kill(agent_id)
                else:
                    process_manager.terminate(agent_id, timeout=2.0)
                terminated_agents.append(agent_id)
            except Exception as e:
                logger.warning(f"Failed to terminate agent {agent_id}: {e}")
                # Try force kill by PID
                if force and agent.pid:
                    try:
                        os.kill(agent.pid, signal.SIGKILL)
                        terminated_agents.append(agent_id)
                    except ProcessLookupError:
                        terminated_agents.append(agent_id)  # Already dead
                    except Exception as kill_e:
                        logger.error(f"Failed to force kill PID {agent.pid}: {kill_e}")

            # Update agent state
            def make_updater():
                def updater(a):
                    a.status = AgentStatus.TERMINATED
                    a.finished_at = datetime.now()
                    return a

                return updater

            agent_store.update(agent_id, make_updater())

    # Update session status
    def session_updater(s: PipelineSession) -> PipelineSession:
        s.status = PipelineSessionStatus.STOPPED
        s.finished_at = datetime.now()
        return s

    session_store.update(session_id, session_updater)

    logger.info(
        f"Stopped session {session_id} of pipeline {pipeline_id}, terminated {len(terminated_agents)} agents"
    )

    return PipelineActionResponse(
        status="stopped",
        message=f"Session stopped ({len(terminated_agents)} agents terminated)",
        pipeline_id=pipeline_id,
    )


@router.delete("/{pipeline_id}/sessions/{session_id}")
async def delete_pipeline_session(
    pipeline_id: str,
    session_id: str,
    pipeline_store: Annotated[PipelineStateStore, Depends(get_pipeline_store)],
    session_store: Annotated[PipelineSessionStore, Depends(get_pipeline_session_store)],
    pipeline_executor: Annotated[PipelineExecutor, Depends(get_pipeline_executor)],
    force: bool = Query(
        default=False, description="Force stop running agents before delete"
    ),
) -> dict:
    """Delete a pipeline session and optionally terminate its agents."""
    import os
    import signal
    from ...models import AgentStatus, PipelineSessionStatus

    # Verify pipeline exists
    pipeline = pipeline_store.get(pipeline_id)
    if pipeline is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline not found: {pipeline_id}"
        )

    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    if session.pipeline_id != pipeline_id:
        raise HTTPException(
            status_code=400,
            detail=f"Session {session_id} does not belong to pipeline {pipeline_id}",
        )

    # If session is running and not force, reject
    if session.is_running() and not force:
        raise HTTPException(
            status_code=400,
            detail="Session is still running. Use force=true to stop and delete.",
        )

    agent_store = pipeline_executor._agent_store
    process_manager = pipeline_executor._process_manager

    # Collect all agents: from node_agent_map + any with matching pipeline_id created during session
    agent_ids_from_map = set(session.node_agent_map.values())

    # Also find any agents with this pipeline_id that were created during the session
    session_start = session.started_at
    all_agent_ids = set()
    for agent_id in agent_store.keys():
        agent = agent_store.get(agent_id)
        if agent and agent.pipeline_id == pipeline_id:
            # Include if in node_agent_map OR created during this session
            if agent_id in agent_ids_from_map:
                all_agent_ids.add(agent_id)
            elif agent.created_at >= session_start:
                all_agent_ids.add(agent_id)

    agent_ids = list(all_agent_ids)
    logger.info(
        f"Found {len(agent_ids)} agents to delete for session {session_id}: {agent_ids}"
    )

    # 1. Stop all running agents
    for agent_id in agent_ids:
        agent = agent_store.get(agent_id)
        if agent and agent.is_running():
            try:
                process_manager.kill(agent_id)
            except Exception:
                if agent.pid:
                    try:
                        os.kill(agent.pid, signal.SIGKILL)
                    except Exception:
                        pass

            def make_updater():
                def updater(a):
                    a.status = AgentStatus.TERMINATED
                    a.finished_at = datetime.now()
                    return a

                return updater

            agent_store.update(agent_id, make_updater())

    # 2. Update session status to stopped
    def session_updater(s: PipelineSession) -> PipelineSession:
        if s.status == PipelineSessionStatus.RUNNING:
            s.status = PipelineSessionStatus.STOPPED
            s.finished_at = datetime.now()
        return s

    session_store.update(session_id, session_updater)

    # 3. Delete all agents
    for agent_id in agent_ids:
        try:
            # Clean up process manager resources
            process_manager.cleanup(agent_id)
        except Exception as e:
            logger.warning(f"Failed to cleanup process for agent {agent_id}: {e}")
        deleted = agent_store.delete(agent_id)
        logger.info(f"Deleted agent {agent_id}: {deleted}")

    # 4. Delete session
    session_store.delete(session_id)

    logger.info(
        f"Deleted session {session_id} of pipeline {pipeline_id} and {len(agent_ids)} agents"
    )

    return {"status": "deleted", "session_id": session_id, "pipeline_id": pipeline_id}
