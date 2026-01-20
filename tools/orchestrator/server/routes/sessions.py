"""Session API routes for the orchestrator server."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ...core import AgentStateStore, ProcessManager, SessionManager
from ...exceptions import SessionNotFoundError
from ...models import (
    AgentState,
    AgentStatus,
    ResumeSessionRequest,
    ResumeSessionResponse,
    SessionListResponse,
    SessionStateResponse,
    SessionStatus,
)
from ..dependencies import get_agent_store, get_process_manager, get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
    status: SessionStatus | None = None,
    backend: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
) -> SessionListResponse:
    """List all sessions with optional filtering."""
    from ...models import AgentBackendType

    backend_type = None
    if backend:
        try:
            backend_type = AgentBackendType(backend)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid backend: {backend}")

    sessions = session_manager.list_sessions(
        backend=backend_type,
        status=status,
        limit=limit,
    )

    return SessionListResponse(
        sessions=[s.metadata for s in sessions],
        total=session_manager.count(),
    )


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session(
    session_id: str,
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> SessionStateResponse:
    """Get the state of a specific session."""
    try:
        session = session_manager.get_session(session_id)
        return SessionStateResponse(session=session)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")


@router.post("/{session_id}/resume", response_model=ResumeSessionResponse)
async def resume_session(
    session_id: str,
    request: ResumeSessionRequest,
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
    agent_store: Annotated[AgentStateStore, Depends(get_agent_store)],
    process_manager: Annotated[ProcessManager, Depends(get_process_manager)],
) -> ResumeSessionResponse:
    """Resume a session by spawning a new agent with the session's context."""
    try:
        session = session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    if not session.metadata.backend_session_id:
        raise HTTPException(
            status_code=400,
            detail="Session has no backend session ID for resumption",
        )

    from ...models import AgentConfig

    # Create config for resumption
    config = AgentConfig(
        backend=session.metadata.backend,
        prompt=request.prompt,
        working_directory=session.metadata.working_directory,
        session_id=session.metadata.backend_session_id,
        resume_session=True,
        max_turns=request.max_turns,
        timeout_seconds=request.timeout_seconds,
    )

    # Create and spawn agent
    agent = AgentState(
        config=config,
        status=AgentStatus.STARTING,
        session_id=session_id,
    )
    agent_store.set(agent.id, agent)

    try:
        managed = process_manager.spawn(agent)

        # Update agent state
        def agent_updater(a: AgentState) -> AgentState:
            a.status = AgentStatus.RUNNING
            a.pid = managed.process.pid
            a.started_at = datetime.now()
            return a

        agent_store.update(agent.id, agent_updater)

        # Update session
        session_manager.update_session(
            session_id,
            status=SessionStatus.ACTIVE,
            add_agent_id=agent.id,
        )

        return ResumeSessionResponse(
            agent_id=agent.id,
            session_id=session_id,
            message=f"Session resumed with agent {agent.id}",
        )

    except Exception as e:
        error_msg = str(e)

        def make_fail_updater(msg: str):
            def updater(a: AgentState) -> AgentState:
                a.status = AgentStatus.FAILED
                a.error_message = msg
                a.finished_at = datetime.now()
                return a

            return updater

        agent_store.update(agent.id, make_fail_updater(error_msg))
        logger.exception(f"Failed to resume session {session_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume session: {error_msg}",
        ) from e


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> dict:
    """Delete a session."""
    deleted = session_manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return {"status": "deleted", "session_id": session_id}


@router.patch("/{session_id}")
async def update_session(
    session_id: str,
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
    status: SessionStatus | None = None,
    tags: list[str] | None = None,
) -> SessionStateResponse:
    """Update session metadata."""
    try:
        session = session_manager.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    if status:
        session_manager.update_session(session_id, status=status)

    if tags is not None:
        session.metadata.tags = tags
        session.touch()
        # Re-persist by getting and updating
        session_manager._store.set(session_id, session)

    session = session_manager.get_session(session_id)
    return SessionStateResponse(session=session)
