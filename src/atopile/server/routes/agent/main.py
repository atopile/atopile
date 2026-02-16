"""Agent chat and orchestration routes."""

from __future__ import annotations

import asyncio
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from atopile.dataclasses import AppContext
from atopile.server.domains.deps import get_ctx

from .models import (
    DEFAULT_AGENT_ID,
    DETAIL_TEXT_APPLYING_GUIDANCE,
    ERROR_CANCELLED_BY_USER,
    ERROR_MESSAGE_EMPTY,
    EVENT_RUN_CANCELLED,
    EVENT_RUN_CREATED,
    EVENT_RUN_PROGRESS,
    EVENT_RUN_STEER_QUEUED,
    EVENT_SESSION_CREATED,
    EVENT_SESSION_PROJECT_SWITCHED,
    EVENT_TURN_FAILED,
    EVENT_TURN_STARTED,
    PHASE_ERROR,
    PHASE_STOPPED,
    PHASE_THINKING,
    REASON_CANCELLED_BY_USER,
    RUN_STATUS_CANCELLED,
    RUN_STATUS_RUNNING,
    STATUS_TEXT_STEERING,
    TURN_MODE_BACKGROUND,
    TURN_MODE_SYNC,
    AgentPeerMessageResponse,
    AgentRun,
    AgentSession,
    CancelRunResponse,
    CreateRunRequest,
    CreateRunResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    GetRunMessagesResponse,
    GetRunResponse,
    SendMessageRequest,
    SendMessageResponse,
    SessionSkillsResponse,
    SteerRunRequest,
    SteerRunResponse,
    active_run_conflict_detail,
    run_not_found_detail,
    session_not_found_detail,
)
from .tools import router as tools_router
from .utils import (
    build_run_trace_callback,
    build_send_message_response,
    cleanup_finished_runs,
    emit_agent_message,
    emit_agent_progress,
    ensure_session_idle,
    log_session_event,
    normalize_running_run_state,
    orchestrator,
    persist_sessions_state,
    pull_agent_run_messages,
    reset_session_state,
    run_turn_in_background,
    runs_by_id,
    runs_lock,
    sessions_by_id,
    sessions_lock,
)

router = APIRouter(prefix="/api/agent", tags=["agent"])
router.include_router(tools_router)


def _ensure_project_scope(
    session_id: str,
    session: AgentSession,
    project_root: str,
) -> None:
    """Reset the session if the request switches to another project root."""
    if session.project_root == project_root:
        return

    log_session_event(
        EVENT_SESSION_PROJECT_SWITCHED,
        {
            "session_id": session_id,
            "from_project_root": session.project_root,
            "to_project_root": project_root,
        },
    )
    reset_session_state(session, project_root=project_root)
    persist_sessions_state()


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    ctx: AppContext = Depends(get_ctx),
):
    try:
        from atopile.server.agent.tools import validate_tool_scope

        validate_tool_scope(request.project_root, ctx)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    session_id = uuid.uuid4().hex
    session = AgentSession(session_id=session_id, project_root=request.project_root)

    with sessions_lock:
        sessions_by_id[session_id] = session
    persist_sessions_state()

    log_session_event(
        EVENT_SESSION_CREATED,
        {
            "session_id": session_id,
            "project_root": request.project_root,
        },
    )

    return CreateSessionResponse(sessionId=session_id, projectRoot=request.project_root)


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    ctx: AppContext = Depends(get_ctx),
):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail=ERROR_MESSAGE_EMPTY)

    cleanup_finished_runs()

    with sessions_lock:
        session = sessions_by_id.get(session_id)

    if not session:
        raise HTTPException(
            status_code=404, detail=session_not_found_detail(session_id)
        )

    active_run = ensure_session_idle(session)
    if active_run and active_run.status == RUN_STATUS_RUNNING:
        raise HTTPException(
            status_code=409,
            detail=active_run_conflict_detail(active_run.run_id),
        )

    _ensure_project_scope(session_id, session, request.project_root)
    session.recent_selected_targets = list(request.selected_targets)

    run_id = uuid.uuid4().hex
    log_session_event(
        EVENT_TURN_STARTED,
        {
            "session_id": session_id,
            "run_id": run_id,
            "mode": TURN_MODE_SYNC,
            "project_root": request.project_root,
            "selected_targets": list(request.selected_targets),
            "message": request.message,
        },
    )

    async def emit_progress(payload: dict) -> None:
        await emit_agent_progress(
            session_id=session_id,
            project_root=request.project_root,
            run_id=run_id,
            payload=payload,
        )

    async def emit_message(message: dict) -> None:
        await emit_agent_message(
            session_id=session_id,
            project_root=request.project_root,
            run_id=run_id,
            message=message,
        )

    trace_callback, trace_log_path = build_run_trace_callback(
        session_id=session_id,
        run_id=run_id,
        project_root=request.project_root,
    )
    if trace_log_path:
        log_session_event(
            EVENT_RUN_PROGRESS,
            {
                "run_id": run_id,
                "session_id": session_id,
                "project_root": request.project_root,
                "phase": "trace",
                "status_text": "Tracing enabled",
                "detail_text": trace_log_path,
            },
        )

    try:
        result = await orchestrator.run_turn(
            ctx=ctx,
            project_root=request.project_root,
            history=list(session.history),
            user_message=request.message,
            selected_targets=request.selected_targets,
            previous_response_id=session.last_response_id,
            tool_memory=session.tool_memory,
            progress_callback=emit_progress,
            message_callback=emit_message,
            trace_callback=trace_callback,
        )
    except Exception as exc:
        await emit_progress({"phase": PHASE_ERROR, "error": str(exc)})
        log_session_event(
            EVENT_TURN_FAILED,
            {
                "session_id": session_id,
                "run_id": run_id,
                "mode": TURN_MODE_SYNC,
                "project_root": request.project_root,
                "error": str(exc),
            },
        )
        raise HTTPException(status_code=500, detail=str(exc))

    response = build_send_message_response(
        session=session,
        user_message=request.message,
        result=result,
        mode=TURN_MODE_SYNC,
        run_id=run_id,
    )
    persist_sessions_state()
    return response


@router.post("/sessions/{session_id}/runs", response_model=CreateRunResponse)
async def create_run(
    session_id: str,
    request: CreateRunRequest,
    ctx: AppContext = Depends(get_ctx),
):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail=ERROR_MESSAGE_EMPTY)

    cleanup_finished_runs()

    with sessions_lock:
        session = sessions_by_id.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail=session_not_found_detail(session_id)
        )

    _ensure_project_scope(session_id, session, request.project_root)

    active_run = ensure_session_idle(session)
    if active_run and active_run.status == RUN_STATUS_RUNNING:
        raise HTTPException(
            status_code=409,
            detail=active_run_conflict_detail(active_run.run_id),
        )

    run_id = uuid.uuid4().hex
    run = AgentRun(
        run_id=run_id,
        session_id=session_id,
        message=request.message,
        project_root=request.project_root,
        selected_targets=list(request.selected_targets),
        status=RUN_STATUS_RUNNING,
    )

    with runs_lock:
        runs_by_id[run_id] = run
    with sessions_lock:
        current = sessions_by_id.get(session_id)
        if current:
            current.recent_selected_targets = list(request.selected_targets)
            current.active_run_id = run_id

    persist_sessions_state()
    log_session_event(
        EVENT_RUN_CREATED,
        {
            "run_id": run_id,
            "session_id": session_id,
            "mode": TURN_MODE_BACKGROUND,
            "project_root": request.project_root,
            "selected_targets": list(request.selected_targets),
            "message": request.message,
        },
    )

    run.task = asyncio.create_task(
        run_turn_in_background(run_id=run_id, session_id=session_id, ctx=ctx)
    )
    return CreateRunResponse(runId=run_id, status=RUN_STATUS_RUNNING)


@router.get("/sessions/{session_id}/runs/{run_id}", response_model=GetRunResponse)
async def get_run(
    session_id: str,
    run_id: str,
):
    cleanup_finished_runs()

    with runs_lock:
        run = runs_by_id.get(run_id)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=run_not_found_detail(run_id))

    response = (
        SendMessageResponse.model_validate(run.response_payload)
        if run.response_payload
        else None
    )
    return GetRunResponse(
        runId=run.run_id,
        status=run.status,
        response=response,
        error=run.error,
    )


@router.get(
    "/sessions/{session_id}/runs/{run_id}/messages",
    response_model=GetRunMessagesResponse,
)
async def get_run_messages(
    session_id: str,
    run_id: str,
    agent: str = Query(default=DEFAULT_AGENT_ID),
    limit: int = Query(default=200, ge=1, le=500),
):
    with runs_lock:
        run = runs_by_id.get(run_id)
        if run:
            run = normalize_running_run_state(run)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=run_not_found_detail(run_id))

    messages = pull_agent_run_messages(
        run_id,
        agent_id=agent.strip().lower() or DEFAULT_AGENT_ID,
        max_items=limit,
    )
    with runs_lock:
        current = runs_by_id.get(run_id)
        pending_acks = len(current.pending_acks) if current else 0

    return GetRunMessagesResponse(
        runId=run_id,
        sessionId=session_id,
        count=len(messages),
        pendingAcks=pending_acks,
        messages=[
            AgentPeerMessageResponse.model_validate(message)
            for message in messages
            if isinstance(message, dict)
        ],
    )


@router.post(
    "/sessions/{session_id}/runs/{run_id}/steer",
    response_model=SteerRunResponse,
)
async def steer_run(
    session_id: str,
    run_id: str,
    request: SteerRunRequest,
):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGE_EMPTY)

    with runs_lock:
        run = runs_by_id.get(run_id)
        if run:
            run = normalize_running_run_state(run)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=run_not_found_detail(run_id))

    if run.status != RUN_STATUS_RUNNING:
        return SteerRunResponse(
            runId=run_id,
            status=run.status,
            queuedMessages=0,
        )

    with runs_lock:
        current = runs_by_id.get(run_id)
        if current is None:
            raise HTTPException(status_code=404, detail=run_not_found_detail(run_id))

        current = normalize_running_run_state(current)
        if current.status != RUN_STATUS_RUNNING:
            return SteerRunResponse(
                runId=run_id,
                status=current.status,
                queuedMessages=0,
            )

        current.steer_messages.append(message)
        current.updated_at = time.time()
        queued_count = len(current.steer_messages)
        run_project_root = current.project_root

    await emit_agent_progress(
        session_id=session_id,
        project_root=run_project_root,
        run_id=run_id,
        payload={
            "phase": PHASE_THINKING,
            "status_text": STATUS_TEXT_STEERING,
            "detail_text": DETAIL_TEXT_APPLYING_GUIDANCE,
        },
    )
    log_session_event(
        EVENT_RUN_STEER_QUEUED,
        {
            "run_id": run_id,
            "session_id": session_id,
            "project_root": run_project_root,
            "queued_messages": queued_count,
            "message": message,
        },
    )
    return SteerRunResponse(
        runId=run_id,
        status=RUN_STATUS_RUNNING,
        queuedMessages=queued_count,
    )


@router.post(
    "/sessions/{session_id}/runs/{run_id}/cancel",
    response_model=CancelRunResponse,
)
async def cancel_run(
    session_id: str,
    run_id: str,
):
    with runs_lock:
        run = runs_by_id.get(run_id)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=run_not_found_detail(run_id))

    if run.status != RUN_STATUS_RUNNING:
        return CancelRunResponse(runId=run.run_id, status=run.status, error=run.error)

    task = run.task
    with runs_lock:
        current = runs_by_id.get(run_id)
        if current:
            current.status = RUN_STATUS_CANCELLED
            current.error = ERROR_CANCELLED_BY_USER
            current.updated_at = time.time()

    with sessions_lock:
        session = sessions_by_id.get(session_id)
        if session and session.active_run_id == run_id:
            session.active_run_id = None
    persist_sessions_state()

    if task and not task.done():
        task.cancel()

    await emit_agent_progress(
        session_id=session_id,
        project_root=run.project_root,
        run_id=run_id,
        payload={"phase": PHASE_STOPPED, "reason": REASON_CANCELLED_BY_USER},
    )
    log_session_event(
        EVENT_RUN_CANCELLED,
        {
            "run_id": run_id,
            "session_id": session_id,
            "project_root": run.project_root,
        },
    )

    return CancelRunResponse(
        runId=run_id,
        status=RUN_STATUS_CANCELLED,
        error=ERROR_CANCELLED_BY_USER,
    )


@router.get(
    "/sessions/{session_id}/skills",
    response_model=SessionSkillsResponse,
)
async def get_session_skills(
    session_id: str,
):
    with sessions_lock:
        session = sessions_by_id.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail=session_not_found_detail(session_id)
        )

    skills_dir = orchestrator.skills_dir
    state = dict(session.skill_state)
    selected_skill_ids = [
        str(value)
        for value in state.get("selected_skill_ids", [])
        if isinstance(value, str)
    ]
    return SessionSkillsResponse(
        sessionId=session.session_id,
        projectRoot=session.project_root,
        skillsDir=str(skills_dir),
        selectedSkillIds=selected_skill_ids,
        selectedSkills=[
            item for item in state.get("selected_skills", []) if isinstance(item, dict)
        ],
        reasoning=[
            str(value) for value in state.get("reasoning", []) if isinstance(value, str)
        ],
        totalChars=int(state.get("total_chars", 0) or 0),
        generatedAt=(
            float(state["generated_at"])
            if isinstance(state.get("generated_at"), (int, float))
            else None
        ),
        loadedSkillsCount=len(selected_skill_ids),
    )
