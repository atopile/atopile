"""Agent chat API routes."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from atopile.dataclasses import AppContext
from atopile.server.agent import AgentOrchestrator, mediator
from atopile.server.domains.deps import get_ctx
from atopile.server.events import get_event_bus
from faebryk.libs.paths import get_log_dir

router = APIRouter(prefix="/api/agent", tags=["agent"])
log = logging.getLogger(__name__)


@dataclass
class AgentSession:
    session_id: str
    project_root: str
    history: list[dict[str, str]] = field(default_factory=list)
    tool_memory: dict[str, dict[str, Any]] = field(default_factory=dict)
    recent_selected_targets: list[str] = field(default_factory=list)
    active_run_id: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class AgentRun:
    run_id: str
    session_id: str
    message: str
    project_root: str
    selected_targets: list[str] = field(default_factory=list)
    status: str = "running"
    response_payload: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    task: asyncio.Task[Any] | None = field(default=None, repr=False)


class CreateSessionRequest(BaseModel):
    project_root: str = Field(alias="projectRoot")

    class Config:
        populate_by_name = True


class CreateSessionResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    project_root: str = Field(alias="projectRoot")

    class Config:
        populate_by_name = True


class SendMessageRequest(BaseModel):
    message: str
    project_root: str = Field(alias="projectRoot")
    selected_targets: list[str] = Field(default_factory=list, alias="selectedTargets")

    class Config:
        populate_by_name = True


class ToolTraceResponse(BaseModel):
    name: str
    args: dict
    ok: bool
    result: dict


class SendMessageResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    assistant_message: str = Field(alias="assistantMessage")
    model: str
    tool_traces: list[ToolTraceResponse] = Field(
        default_factory=list, alias="toolTraces"
    )
    tool_suggestions: list[dict] = Field(default_factory=list, alias="toolSuggestions")
    tool_memory: list[dict] = Field(default_factory=list, alias="toolMemory")

    class Config:
        populate_by_name = True


class ToolDirectoryResponse(BaseModel):
    tools: list[dict] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    suggestions: list[dict] = Field(default_factory=list)
    tool_memory: list[dict] = Field(default_factory=list, alias="toolMemory")

    class Config:
        populate_by_name = True


class ToolSuggestionsRequest(BaseModel):
    message: str = ""
    project_root: str | None = Field(default=None, alias="projectRoot")
    selected_targets: list[str] = Field(default_factory=list, alias="selectedTargets")

    class Config:
        populate_by_name = True


class ToolSuggestionsResponse(BaseModel):
    suggestions: list[dict] = Field(default_factory=list)
    tool_memory: list[dict] = Field(default_factory=list, alias="toolMemory")

    class Config:
        populate_by_name = True


class CreateRunRequest(BaseModel):
    message: str
    project_root: str = Field(alias="projectRoot")
    selected_targets: list[str] = Field(default_factory=list, alias="selectedTargets")

    class Config:
        populate_by_name = True


class CreateRunResponse(BaseModel):
    run_id: str = Field(alias="runId")
    status: str

    class Config:
        populate_by_name = True


class GetRunResponse(BaseModel):
    run_id: str = Field(alias="runId")
    status: str
    response: SendMessageResponse | None = None
    error: str | None = None

    class Config:
        populate_by_name = True


class CancelRunResponse(BaseModel):
    run_id: str = Field(alias="runId")
    status: str
    error: str | None = None

    class Config:
        populate_by_name = True


_sessions: dict[str, AgentSession] = {}
_sessions_lock = threading.Lock()
_runs: dict[str, AgentRun] = {}
_runs_lock = threading.Lock()
_session_log_lock = threading.Lock()
_orchestrator = AgentOrchestrator()


def _get_agent_session_log_path() -> Path:
    override = os.getenv("ATOPILE_AGENT_SESSION_LOG_PATH")
    if override and override.strip():
        return Path(override).expanduser()
    return get_log_dir() / "agent_sessions.jsonl"


def _log_session_event(event: str, payload: dict[str, Any]) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    log_path = _get_agent_session_log_path()
    try:
        encoded = json.dumps(record, ensure_ascii=False, default=str)
        with _session_log_lock:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(encoded + "\n")
    except Exception:
        log.exception("Failed to append agent session log event")


def _build_send_message_response(
    *,
    session: AgentSession,
    user_message: str,
    result: Any,
    mode: str,
    run_id: str | None = None,
) -> SendMessageResponse:
    session.history.append({"role": "user", "content": user_message})
    session.history.append({"role": "assistant", "content": result.text})
    session.tool_memory = mediator.update_tool_memory(
        session.tool_memory,
        result.tool_traces,
    )
    session.updated_at = time.time()

    suggestions = mediator.suggest_tools(
        message="",
        history=list(session.history),
        selected_targets=session.recent_selected_targets,
        tool_memory=session.tool_memory,
        limit=3,
    )
    tool_memory_view = mediator.get_tool_memory_view(session.tool_memory)

    response = SendMessageResponse(
        sessionId=session.session_id,
        assistantMessage=result.text,
        model=result.model,
        toolTraces=[
            ToolTraceResponse(
                name=trace.name, args=trace.args, ok=trace.ok, result=trace.result
            )
            for trace in result.tool_traces
        ],
        toolSuggestions=suggestions,
        toolMemory=tool_memory_view,
    )
    _log_session_event(
        "turn_completed",
        {
            "session_id": session.session_id,
            "run_id": run_id,
            "mode": mode,
            "project_root": session.project_root,
            "selected_targets": list(session.recent_selected_targets),
            "user_message": user_message,
            "assistant_message": result.text,
            "model": result.model,
            "tool_trace_count": len(response.tool_traces),
            "tool_traces": [trace.model_dump() for trace in response.tool_traces],
        },
    )
    return response


async def _emit_agent_progress(
    *,
    session_id: str,
    project_root: str,
    run_id: str | None,
    payload: dict[str, Any],
) -> None:
    event_payload: dict[str, Any] = {
        "session_id": session_id,
        "project_root": project_root,
        **payload,
    }
    if run_id:
        event_payload["run_id"] = run_id
    await get_event_bus().emit("agent_progress", event_payload)


def _cleanup_finished_runs(max_age_seconds: float = 3_600.0) -> None:
    now = time.time()
    to_delete: list[str] = []
    with _runs_lock:
        for run_id, run in _runs.items():
            if run.status == "running":
                continue
            if (now - run.updated_at) <= max_age_seconds:
                continue
            to_delete.append(run_id)
        for run_id in to_delete:
            _runs.pop(run_id, None)


async def _run_turn_in_background(
    *,
    run_id: str,
    session_id: str,
    ctx: AppContext,
) -> None:
    with _runs_lock:
        run = _runs.get(run_id)
    if run is None:
        return

    with _sessions_lock:
        session = _sessions.get(session_id)
    if session is None:
        with _runs_lock:
            missing = _runs.get(run_id)
            if missing:
                missing.status = "failed"
                missing.error = f"Session not found: {session_id}"
                missing.updated_at = time.time()
        _log_session_event(
            "run_failed",
            {
                "run_id": run_id,
                "session_id": session_id,
                "error": f"Session not found: {session_id}",
            },
        )
        return

    async def emit_progress(payload: dict) -> None:
        await _emit_agent_progress(
            session_id=session_id,
            project_root=run.project_root,
            run_id=run_id,
            payload=payload,
        )

    try:
        result = await _orchestrator.run_turn(
            ctx=ctx,
            project_root=run.project_root,
            history=list(session.history),
            user_message=run.message,
            selected_targets=run.selected_targets,
            progress_callback=emit_progress,
        )
    except asyncio.CancelledError:
        with _runs_lock:
            cancelled = _runs.get(run_id)
            if cancelled and cancelled.status == "running":
                cancelled.status = "cancelled"
                cancelled.error = "Cancelled"
                cancelled.updated_at = time.time()
        with _sessions_lock:
            current = _sessions.get(session_id)
            if current and current.active_run_id == run_id:
                current.active_run_id = None
        return
    except Exception as exc:
        await emit_progress({"phase": "error", "error": str(exc)})
        with _runs_lock:
            failed = _runs.get(run_id)
            if failed:
                failed.status = "failed"
                failed.error = str(exc)
                failed.updated_at = time.time()
        with _sessions_lock:
            current = _sessions.get(session_id)
            if current and current.active_run_id == run_id:
                current.active_run_id = None
        _log_session_event(
            "run_failed",
            {
                "run_id": run_id,
                "session_id": session_id,
                "project_root": run.project_root,
                "error": str(exc),
            },
        )
        return

    with _sessions_lock:
        active_session = _sessions.get(session_id)
        if active_session is None:
            with _runs_lock:
                failed = _runs.get(run_id)
                if failed:
                    failed.status = "failed"
                    failed.error = "Session expired before run completion"
                    failed.updated_at = time.time()
            _log_session_event(
                "run_failed",
                {
                    "run_id": run_id,
                    "session_id": session_id,
                    "project_root": run.project_root,
                    "error": "Session expired before run completion",
                },
            )
            return

        with _runs_lock:
            latest = _runs.get(run_id)
            if latest is not None and latest.status != "running":
                return

        response = _build_send_message_response(
            session=active_session,
            user_message=run.message,
            result=result,
            mode="background",
            run_id=run_id,
        )
        if active_session.active_run_id == run_id:
            active_session.active_run_id = None

    with _runs_lock:
        completed = _runs.get(run_id)
        if completed:
            if completed.status != "running":
                return
            completed.status = "completed"
            completed.error = None
            completed.response_payload = response.model_dump(by_alias=True)
            completed.updated_at = time.time()
    _log_session_event(
        "run_completed",
        {
            "run_id": run_id,
            "session_id": session_id,
            "project_root": run.project_root,
            "tool_trace_count": len(response.tool_traces),
        },
    )


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest, ctx: AppContext = Depends(get_ctx)
):
    try:
        from atopile.server.agent.tools import validate_tool_scope

        validate_tool_scope(request.project_root, ctx)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    session_id = uuid.uuid4().hex
    session = AgentSession(session_id=session_id, project_root=request.project_root)

    with _sessions_lock:
        _sessions[session_id] = session
    _log_session_event(
        "session_created",
        {
            "session_id": session_id,
            "project_root": request.project_root,
        },
    )

    return CreateSessionResponse(sessionId=session_id, projectRoot=request.project_root)


@router.post("/session", response_model=CreateSessionResponse)
async def create_session_legacy(
    request: CreateSessionRequest, ctx: AppContext = Depends(get_ctx)
):
    """Legacy alias for clients using singular session path."""
    return await create_session(request, ctx)


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    ctx: AppContext = Depends(get_ctx),
):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    _cleanup_finished_runs()

    with _sessions_lock:
        session = _sessions.get(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    with _runs_lock:
        active_run = _runs.get(session.active_run_id or "")
        if active_run and active_run.status == "running":
            raise HTTPException(
                status_code=409,
                detail="Another agent run is already active for this session.",
            )

    if session.project_root != request.project_root:
        # Keep scope strict per selected project.
        # Clear cross-project conversation state.
        _log_session_event(
            "session_project_switched",
            {
                "session_id": session_id,
                "from_project_root": session.project_root,
                "to_project_root": request.project_root,
            },
        )
        session.project_root = request.project_root
        session.history = []
        session.tool_memory = {}
        session.active_run_id = None

    session.recent_selected_targets = list(request.selected_targets)
    run_id = uuid.uuid4().hex
    _log_session_event(
        "turn_started",
        {
            "session_id": session_id,
            "run_id": run_id,
            "mode": "sync",
            "project_root": request.project_root,
            "selected_targets": list(request.selected_targets),
            "message": request.message,
        },
    )

    async def emit_progress(payload: dict) -> None:
        await _emit_agent_progress(
            session_id=session_id,
            project_root=request.project_root,
            run_id=run_id,
            payload=payload,
        )

    try:
        result = await _orchestrator.run_turn(
            ctx=ctx,
            project_root=request.project_root,
            history=list(session.history),
            user_message=request.message,
            selected_targets=request.selected_targets,
            progress_callback=emit_progress,
        )
    except Exception as exc:
        await emit_progress(
            {
                "phase": "error",
                "error": str(exc),
            }
        )
        _log_session_event(
            "turn_failed",
            {
                "session_id": session_id,
                "run_id": run_id,
                "mode": "sync",
                "project_root": request.project_root,
                "error": str(exc),
            },
        )
        raise HTTPException(status_code=500, detail=str(exc))

    return _build_send_message_response(
        session=session,
        user_message=request.message,
        result=result,
        mode="sync",
        run_id=run_id,
    )


@router.post("/session/{session_id}/message", response_model=SendMessageResponse)
async def send_message_legacy(
    session_id: str,
    request: SendMessageRequest,
    ctx: AppContext = Depends(get_ctx),
):
    """Legacy alias for clients using singular message path."""
    return await send_message(session_id, request, ctx)


@router.post("/sessions/{session_id}/runs", response_model=CreateRunResponse)
async def create_run(
    session_id: str,
    request: CreateRunRequest,
    ctx: AppContext = Depends(get_ctx),
):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    _cleanup_finished_runs()

    with _sessions_lock:
        session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    if session.project_root != request.project_root:
        _log_session_event(
            "session_project_switched",
            {
                "session_id": session_id,
                "from_project_root": session.project_root,
                "to_project_root": request.project_root,
            },
        )
        session.project_root = request.project_root
        session.history = []
        session.tool_memory = {}
        session.active_run_id = None

    with _runs_lock:
        active_run = _runs.get(session.active_run_id or "")
        if active_run and active_run.status == "running":
            raise HTTPException(
                status_code=409,
                detail="Another agent run is already active for this session.",
            )

    run_id = uuid.uuid4().hex
    run = AgentRun(
        run_id=run_id,
        session_id=session_id,
        message=request.message,
        project_root=request.project_root,
        selected_targets=list(request.selected_targets),
        status="running",
    )

    with _runs_lock:
        _runs[run_id] = run
    with _sessions_lock:
        current = _sessions.get(session_id)
        if current:
            current.recent_selected_targets = list(request.selected_targets)
            current.active_run_id = run_id
    _log_session_event(
        "run_created",
        {
            "run_id": run_id,
            "session_id": session_id,
            "mode": "background",
            "project_root": request.project_root,
            "selected_targets": list(request.selected_targets),
            "message": request.message,
        },
    )

    run.task = asyncio.create_task(
        _run_turn_in_background(run_id=run_id, session_id=session_id, ctx=ctx)
    )
    return CreateRunResponse(runId=run_id, status="running")


@router.get("/sessions/{session_id}/runs/{run_id}", response_model=GetRunResponse)
async def get_run(
    session_id: str,
    run_id: str,
):
    _cleanup_finished_runs()

    with _runs_lock:
        run = _runs.get(run_id)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

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


@router.post(
    "/sessions/{session_id}/runs/{run_id}/cancel",
    response_model=CancelRunResponse,
)
async def cancel_run(
    session_id: str,
    run_id: str,
):
    with _runs_lock:
        run = _runs.get(run_id)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    if run.status != "running":
        return CancelRunResponse(runId=run.run_id, status=run.status, error=run.error)

    task = run.task
    with _runs_lock:
        current = _runs.get(run_id)
        if current:
            current.status = "cancelled"
            current.error = "Cancelled by user"
            current.updated_at = time.time()
    with _sessions_lock:
        session = _sessions.get(session_id)
        if session and session.active_run_id == run_id:
            session.active_run_id = None

    if task and not task.done():
        task.cancel()

    await _emit_agent_progress(
        session_id=session_id,
        project_root=run.project_root,
        run_id=run_id,
        payload={"phase": "stopped", "reason": "cancelled_by_user"},
    )
    _log_session_event(
        "run_cancelled",
        {
            "run_id": run_id,
            "session_id": session_id,
            "project_root": run.project_root,
        },
    )

    return CancelRunResponse(
        runId=run_id,
        status="cancelled",
        error="Cancelled by user",
    )


@router.get("/tools", response_model=ToolDirectoryResponse)
async def get_tool_directory(
    session_id: str | None = Query(default=None, alias="sessionId"),
):
    tool_memory: dict[str, dict[str, Any]] = {}
    history: list[dict[str, str]] = []
    selected_targets: list[str] = []

    if session_id:
        with _sessions_lock:
            session = _sessions.get(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}",
            )
        tool_memory = dict(session.tool_memory)
        history = list(session.history)
        selected_targets = list(session.recent_selected_targets)

    directory = mediator.get_tool_directory()
    categories = sorted({str(item.get("category", "other")) for item in directory})
    suggestions = mediator.suggest_tools(
        message="",
        history=history,
        selected_targets=selected_targets,
        tool_memory=tool_memory,
        limit=3,
    )
    memory_view = mediator.get_tool_memory_view(tool_memory)

    return ToolDirectoryResponse(
        tools=directory,
        categories=categories,
        suggestions=suggestions,
        toolMemory=memory_view,
    )


@router.post(
    "/sessions/{session_id}/tool-suggestions",
    response_model=ToolSuggestionsResponse,
)
async def get_tool_suggestions(
    session_id: str,
    request: ToolSuggestionsRequest,
):
    with _sessions_lock:
        session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    if request.project_root and request.project_root != session.project_root:
        raise HTTPException(
            status_code=400,
            detail="projectRoot must match the active session project",
        )

    selected_targets = (
        list(request.selected_targets)
        if request.selected_targets
        else list(session.recent_selected_targets)
    )
    suggestions = mediator.suggest_tools(
        message=request.message,
        history=list(session.history),
        selected_targets=selected_targets,
        tool_memory=session.tool_memory,
        limit=3,
    )
    memory_view = mediator.get_tool_memory_view(session.tool_memory)

    return ToolSuggestionsResponse(
        suggestions=suggestions,
        toolMemory=memory_view,
    )
