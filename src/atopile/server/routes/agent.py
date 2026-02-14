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
from atopile.server.agent import skills as skills_domain
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
    last_response_id: str | None = None
    conversation_id: str | None = None
    skill_state: dict[str, Any] = field(default_factory=dict)
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
    steer_messages: list[str] = field(default_factory=list)
    message_log: list[dict[str, Any]] = field(default_factory=list)
    inbox_cursor: dict[str, int] = field(
        default_factory=lambda: {"manager": 0, "worker": 0}
    )
    pending_acks: set[str] = field(default_factory=set)
    intent_snapshot: dict[str, Any] = field(default_factory=dict)


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


class AgentPeerMessageResponse(BaseModel):
    message_id: str = Field(alias="messageId")
    thread_id: str = Field(alias="threadId")
    from_agent: str = Field(alias="fromAgent")
    to_agent: str = Field(alias="toAgent")
    kind: str
    summary: str
    payload: dict = Field(default_factory=dict)
    visibility: str
    priority: str
    requires_ack: bool = Field(alias="requiresAck")
    correlation_id: str | None = Field(default=None, alias="correlationId")
    parent_id: str | None = Field(default=None, alias="parentId")
    created_at: float = Field(alias="createdAt")

    class Config:
        populate_by_name = True


class SendMessageResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    assistant_message: str = Field(alias="assistantMessage")
    model: str
    tool_traces: list[ToolTraceResponse] = Field(
        default_factory=list, alias="toolTraces"
    )
    tool_suggestions: list[dict] = Field(default_factory=list, alias="toolSuggestions")
    tool_memory: list[dict] = Field(default_factory=list, alias="toolMemory")
    agent_messages: list[AgentPeerMessageResponse] = Field(
        default_factory=list, alias="agentMessages"
    )

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


class SessionSkillsResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    project_root: str = Field(alias="projectRoot")
    skills_dir: str = Field(alias="skillsDir")
    selected_skill_ids: list[str] = Field(
        default_factory=list,
        alias="selectedSkillIds",
    )
    selected_skills: list[dict] = Field(default_factory=list, alias="selectedSkills")
    reasoning: list[str] = Field(default_factory=list)
    total_chars: int = Field(default=0, alias="totalChars")
    generated_at: float | None = Field(default=None, alias="generatedAt")
    loaded_skills_count: int = Field(default=0, alias="loadedSkillsCount")

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


class GetRunMessagesResponse(BaseModel):
    run_id: str = Field(alias="runId")
    session_id: str = Field(alias="sessionId")
    count: int
    pending_acks: int = Field(alias="pendingAcks")
    messages: list[AgentPeerMessageResponse] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class CancelRunResponse(BaseModel):
    run_id: str = Field(alias="runId")
    status: str
    error: str | None = None

    class Config:
        populate_by_name = True


class SteerRunRequest(BaseModel):
    message: str


class SteerRunResponse(BaseModel):
    run_id: str = Field(alias="runId")
    status: str
    queued_messages: int = Field(alias="queuedMessages")

    class Config:
        populate_by_name = True


_sessions: dict[str, AgentSession] = {}
_sessions_lock = threading.Lock()
_runs: dict[str, AgentRun] = {}
_runs_lock = threading.Lock()
_session_log_lock = threading.Lock()
_orchestrator = AgentOrchestrator()
_SESSION_STATE_VERSION = 1


def _get_agent_session_log_path() -> Path:
    override = os.getenv("ATOPILE_AGENT_SESSION_LOG_PATH")
    if override and override.strip():
        return Path(override).expanduser()
    return get_log_dir() / "agent_sessions.jsonl"


def _get_agent_session_state_path() -> Path:
    override = os.getenv("ATOPILE_AGENT_SESSION_STATE_PATH")
    if override and override.strip():
        return Path(override).expanduser()
    return get_log_dir() / "agent_sessions_state.json"


def _get_max_persisted_history_entries() -> int:
    default_value = 160
    raw = os.getenv("ATOPILE_AGENT_MAX_PERSISTED_HISTORY", str(default_value))
    try:
        parsed = int(raw)
    except ValueError:
        return default_value
    return max(20, min(parsed, 2_000))


def _normalize_history_entries(
    value: Any, *, max_entries: int | None = None
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, str]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            continue
        normalized.append({"role": role, "content": content})
    if max_entries is not None and max_entries > 0 and len(normalized) > max_entries:
        return normalized[-max_entries:]
    return normalized


def _normalize_tool_memory(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for key, entry in value.items():
        if not isinstance(key, str) or not isinstance(entry, dict):
            continue
        normalized[key] = dict(entry)
    return normalized


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _serialize_session_state(session: AgentSession) -> dict[str, Any]:
    max_history = _get_max_persisted_history_entries()
    return {
        "session_id": session.session_id,
        "project_root": session.project_root,
        "history": _normalize_history_entries(session.history, max_entries=max_history),
        "tool_memory": _normalize_tool_memory(session.tool_memory),
        "recent_selected_targets": _normalize_string_list(
            session.recent_selected_targets
        ),
        "last_response_id": (
            session.last_response_id
            if isinstance(session.last_response_id, str)
            else None
        ),
        "conversation_id": (
            session.conversation_id
            if isinstance(session.conversation_id, str)
            else None
        ),
        "skill_state": dict(session.skill_state)
        if isinstance(session.skill_state, dict)
        else {},
        "created_at": float(session.created_at),
        "updated_at": float(session.updated_at),
    }


def _deserialize_session_state(value: Any) -> AgentSession | None:
    if not isinstance(value, dict):
        return None
    session_id = value.get("session_id")
    project_root = value.get("project_root")
    if not isinstance(session_id, str) or not session_id:
        return None
    if not isinstance(project_root, str) or not project_root:
        return None

    created_at_raw = value.get("created_at")
    updated_at_raw = value.get("updated_at")
    created_at = (
        float(created_at_raw)
        if isinstance(created_at_raw, (int, float))
        else time.time()
    )
    updated_at = (
        float(updated_at_raw)
        if isinstance(updated_at_raw, (int, float))
        else created_at
    )
    session = AgentSession(
        session_id=session_id,
        project_root=project_root,
        created_at=created_at,
        updated_at=updated_at,
    )
    session.history = _normalize_history_entries(value.get("history"))
    session.tool_memory = _normalize_tool_memory(value.get("tool_memory"))
    session.recent_selected_targets = _normalize_string_list(
        value.get("recent_selected_targets")
    )
    if isinstance(value.get("last_response_id"), str):
        session.last_response_id = value["last_response_id"]
    if isinstance(value.get("conversation_id"), str):
        session.conversation_id = value["conversation_id"]
    if isinstance(value.get("skill_state"), dict):
        session.skill_state = dict(value["skill_state"])
    return session


def _persist_sessions_state() -> None:
    with _sessions_lock:
        serialized_sessions = [
            _serialize_session_state(session) for session in _sessions.values()
        ]

    payload = {
        "version": _SESSION_STATE_VERSION,
        "saved_at": time.time(),
        "sessions": serialized_sessions,
    }
    state_path = _get_agent_session_state_path()
    tmp_path = state_path.with_suffix(f"{state_path.suffix}.tmp")
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        tmp_path.replace(state_path)
    except Exception:
        log.exception("Failed to persist agent session state")
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


def _load_sessions_state() -> None:
    state_path = _get_agent_session_state_path()
    if not state_path.exists():
        return
    try:
        raw_payload = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        log.exception("Failed to read persisted agent session state")
        return

    raw_sessions: Any = []
    if isinstance(raw_payload, dict):
        raw_sessions = raw_payload.get("sessions", [])
    elif isinstance(raw_payload, list):
        raw_sessions = raw_payload
    if not isinstance(raw_sessions, list):
        return

    restored: dict[str, AgentSession] = {}
    for raw_session in raw_sessions:
        session = _deserialize_session_state(raw_session)
        if session is None:
            continue
        # In-flight run state is always runtime-only.
        session.active_run_id = None
        restored[session.session_id] = session

    if not restored:
        return

    with _sessions_lock:
        _sessions.clear()
        _sessions.update(restored)

    log.info("Restored %d persisted agent sessions", len(restored))


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


_load_sessions_state()


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
    session.last_response_id = result.response_id or session.last_response_id
    if isinstance(result.skill_state, dict):
        session.skill_state = dict(result.skill_state)
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
        agentMessages=[
            AgentPeerMessageResponse.model_validate(message)
            for message in getattr(result, "agent_messages", [])
            if isinstance(message, dict)
        ],
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
            "agent_message_count": len(response.agent_messages),
            "tool_traces": [trace.model_dump() for trace in response.tool_traces],
            "agent_messages": [
                message.model_dump() for message in response.agent_messages
            ],
            "last_response_id": session.last_response_id,
            "skill_state": session.skill_state,
            "context_metrics": getattr(result, "context_metrics", {}),
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


async def _emit_agent_message(
    *,
    session_id: str,
    project_root: str,
    run_id: str,
    message: dict[str, Any],
) -> None:
    await get_event_bus().emit(
        "agent_message",
        {
            "session_id": session_id,
            "project_root": project_root,
            "run_id": run_id,
            "message": message,
        },
    )


def _post_agent_run_message(run_id: str, message: dict[str, Any]) -> None:
    if not isinstance(message, dict):
        return
    with _runs_lock:
        run = _runs.get(run_id)
        if run is None:
            return
        run.message_log.append(dict(message))
        run.updated_at = time.time()
        requires_ack = bool(message.get("requires_ack", False))
        message_id = message.get("message_id")
        if requires_ack and isinstance(message_id, str) and message_id:
            run.pending_acks.add(message_id)
        if message.get("kind") == "ack":
            payload = message.get("payload")
            acked_id = None
            if isinstance(payload, dict):
                payload_id = payload.get("message_id")
                if isinstance(payload_id, str) and payload_id:
                    acked_id = payload_id
            if acked_id:
                run.pending_acks.discard(acked_id)
        if (
            message.get("kind") == "intent_brief"
            and isinstance(message.get("payload"), dict)
            and not run.intent_snapshot
        ):
            run.intent_snapshot = dict(message["payload"])


def _pull_agent_run_messages(
    run_id: str,
    *,
    agent_id: str,
    max_items: int = 50,
) -> list[dict[str, Any]]:
    max_items = max(1, min(max_items, 500))
    with _runs_lock:
        run = _runs.get(run_id)
        if run is None:
            return []
        cursor = run.inbox_cursor.get(agent_id, 0)
        if cursor < 0:
            cursor = 0
        messages = run.message_log[cursor : cursor + max_items]
        run.inbox_cursor[agent_id] = cursor + len(messages)
        run.updated_at = time.time()
    return [dict(message) for message in messages]


def _ack_agent_run_message(
    run_id: str,
    *,
    message_id: str,
) -> bool:
    with _runs_lock:
        run = _runs.get(run_id)
        if run is None:
            return False
        if message_id not in run.pending_acks:
            return False
        run.pending_acks.remove(message_id)
        run.updated_at = time.time()
        return True


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


def _normalize_running_run_state(run: AgentRun) -> AgentRun:
    """Repair stale running runs when their task is already done."""
    if run.status != "running":
        return run
    task = run.task
    if task is None or not task.done():
        return run

    run.status = "failed"
    run.error = "Run task ended unexpectedly"
    run.updated_at = time.time()
    if task.cancelled():
        run.error = "Cancelled"
    else:
        try:
            exc = task.exception()
        except Exception as task_error:
            exc = task_error
        if exc is not None:
            run.error = f"Run task failed: {exc}"
    return run


def _consume_run_steer_messages(run_id: str) -> list[str]:
    with _runs_lock:
        run = _runs.get(run_id)
        if run is None or not run.steer_messages:
            return []
        queued = list(run.steer_messages)
        run.steer_messages.clear()
        run.updated_at = time.time()
    return queued


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

    async def emit_message(message: dict) -> None:
        _post_agent_run_message(run_id, message)
        await _emit_agent_message(
            session_id=session_id,
            project_root=run.project_root,
            run_id=run_id,
            message=message,
        )

    def consume_steering_messages() -> list[str]:
        queued = _consume_run_steer_messages(run_id)
        if queued:
            _log_session_event(
                "run_steer_consumed",
                {
                    "run_id": run_id,
                    "session_id": session_id,
                    "project_root": run.project_root,
                    "count": len(queued),
                },
            )
        return queued

    try:
        result = await _orchestrator.run_turn(
            ctx=ctx,
            project_root=run.project_root,
            history=list(session.history),
            user_message=run.message,
            selected_targets=run.selected_targets,
            previous_response_id=session.last_response_id,
            tool_memory=session.tool_memory,
            progress_callback=emit_progress,
            consume_steering_messages=consume_steering_messages,
            message_callback=emit_message,
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
        _persist_sessions_state()
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
        _persist_sessions_state()
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
    _persist_sessions_state()

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
    _persist_sessions_state()
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
        if active_run:
            active_run = _normalize_running_run_state(active_run)
        if active_run and active_run.status == "running":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Another agent run is already active for this session "
                    f"(run_id={active_run.run_id})."
                ),
            )
    if session.active_run_id and (active_run is None or active_run.status != "running"):
        session.active_run_id = None

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
        session.last_response_id = None
        session.conversation_id = None
        session.skill_state = {}
        _persist_sessions_state()

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

    async def emit_message(message: dict) -> None:
        await _emit_agent_message(
            session_id=session_id,
            project_root=request.project_root,
            run_id=run_id,
            message=message,
        )

    try:
        result = await _orchestrator.run_turn(
            ctx=ctx,
            project_root=request.project_root,
            history=list(session.history),
            user_message=request.message,
            selected_targets=request.selected_targets,
            previous_response_id=session.last_response_id,
            tool_memory=session.tool_memory,
            progress_callback=emit_progress,
            message_callback=emit_message,
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

    response = _build_send_message_response(
        session=session,
        user_message=request.message,
        result=result,
        mode="sync",
        run_id=run_id,
    )
    _persist_sessions_state()
    return response


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
        session.last_response_id = None
        session.conversation_id = None
        session.skill_state = {}
        _persist_sessions_state()

    with _runs_lock:
        active_run = _runs.get(session.active_run_id or "")
        if active_run:
            active_run = _normalize_running_run_state(active_run)
        if active_run and active_run.status == "running":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Another agent run is already active for this session "
                    f"(run_id={active_run.run_id})."
                ),
            )
    if session.active_run_id and (active_run is None or active_run.status != "running"):
        session.active_run_id = None

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
    _persist_sessions_state()
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


@router.get(
    "/sessions/{session_id}/runs/{run_id}/messages",
    response_model=GetRunMessagesResponse,
)
async def get_run_messages(
    session_id: str,
    run_id: str,
    agent: str = Query(default="manager"),
    limit: int = Query(default=200, ge=1, le=500),
):
    with _runs_lock:
        run = _runs.get(run_id)
        if run:
            run = _normalize_running_run_state(run)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    messages = _pull_agent_run_messages(
        run_id,
        agent_id=agent.strip().lower() or "manager",
        max_items=limit,
    )
    with _runs_lock:
        current = _runs.get(run_id)
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
        raise HTTPException(status_code=400, detail="message must not be empty")

    with _runs_lock:
        run = _runs.get(run_id)
        if run:
            run = _normalize_running_run_state(run)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    if run.status != "running":
        return SteerRunResponse(
            runId=run_id,
            status=run.status,
            queuedMessages=0,
        )

    with _runs_lock:
        current = _runs.get(run_id)
        if current is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        current = _normalize_running_run_state(current)
        if current.status != "running":
            return SteerRunResponse(
                runId=run_id,
                status=current.status,
                queuedMessages=0,
            )
        current.steer_messages.append(message)
        current.updated_at = time.time()
        queued_count = len(current.steer_messages)
        run_project_root = current.project_root

    await _emit_agent_progress(
        session_id=session_id,
        project_root=run_project_root,
        run_id=run_id,
        payload={
            "phase": "thinking",
            "status_text": "Steering",
            "detail_text": "Applying latest user guidance",
        },
    )
    _log_session_event(
        "run_steer_queued",
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
        status="running",
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
    _persist_sessions_state()

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


@router.get(
    "/sessions/{session_id}/skills",
    response_model=SessionSkillsResponse,
)
async def get_session_skills(
    session_id: str,
):
    with _sessions_lock:
        session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    skills_dir = _orchestrator.skills_dir
    docs = skills_domain.load_skill_docs(
        skills_dir=skills_dir,
        ttl_s=_orchestrator.skill_index_ttl_s,
    )
    state = dict(session.skill_state)
    return SessionSkillsResponse(
        sessionId=session.session_id,
        projectRoot=session.project_root,
        skillsDir=str(skills_dir),
        selectedSkillIds=[
            str(value)
            for value in state.get("selected_skill_ids", [])
            if isinstance(value, str)
        ],
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
        loadedSkillsCount=len(docs),
    )
