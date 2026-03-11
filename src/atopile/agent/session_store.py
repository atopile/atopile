"""Stateful session/run storage for agent routes."""

from __future__ import annotations

import os
import threading
import time
import uuid
from typing import Any

from atopile.dataclasses import UiAgentMessageData
from atopile.logging import get_logger

from .api_models import (
    ERROR_CANCELLED,
    ERROR_RUN_TASK_ENDED,
    RUN_STATUS_FAILED,
    RUN_STATUS_RUNNING,
    AgentRun,
    AgentSession,
)

DEFAULT_MAX_PERSISTED_HISTORY = 160
MIN_PERSISTED_HISTORY = 20
MAX_PERSISTED_HISTORY = 2_000
DEFAULT_RUN_RETENTION_SECONDS = 3_600.0

sessions_by_id: dict[str, AgentSession] = {}
sessions_lock = threading.Lock()
runs_by_id: dict[str, AgentRun] = {}
runs_lock = threading.Lock()
sync_turns_by_session: dict[str, str] = {}
sync_turns_lock = threading.Lock()
session_execution_lock = threading.Lock()

log = get_logger(__name__)


def _get_max_persisted_history_entries() -> int:
    raw = os.getenv(
        "ATOPILE_AGENT_MAX_PERSISTED_HISTORY", str(DEFAULT_MAX_PERSISTED_HISTORY)
    )
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_MAX_PERSISTED_HISTORY
    return max(MIN_PERSISTED_HISTORY, min(parsed, MAX_PERSISTED_HISTORY))


def _normalize_history_entries(
    value: Any,
    *,
    max_entries: int | None = None,
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    normalized: list[dict[str, str]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if isinstance(role, str) and isinstance(content, str):
            normalized.append({"role": role, "content": content})

    if max_entries is not None and max_entries > 0 and len(normalized) > max_entries:
        return normalized[-max_entries:]
    return normalized


def _normalize_tool_memory(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for key, entry in value.items():
        if isinstance(key, str) and isinstance(entry, dict):
            normalized[key] = dict(entry)
    return normalized


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _normalize_messages(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        try:
            normalized.append(
                UiAgentMessageData.model_validate(entry).model_dump(mode="json")
            )
        except Exception:
            continue
    return normalized


def _serialize_session_state(session: AgentSession) -> dict[str, Any]:
    max_history = _get_max_persisted_history_entries()
    return {
        "session_id": session.session_id,
        "project_root": session.project_root,
        "history": _normalize_history_entries(session.history, max_entries=max_history),
        "messages": _normalize_messages(session.messages),
        "tool_memory": _normalize_tool_memory(session.tool_memory),
        "recent_selected_targets": _normalize_string_list(
            session.recent_selected_targets
        ),
        "activity_label": session.activity_label
        if isinstance(session.activity_label, str) and session.activity_label
        else "Ready",
        "error": session.error if isinstance(session.error, str) else None,
        "run_started_at": (
            float(session.run_started_at)
            if isinstance(session.run_started_at, (int, float))
            else None
        ),
        "last_response_id": session.last_response_id
        if isinstance(session.last_response_id, str)
        else None,
        "conversation_id": session.conversation_id
        if isinstance(session.conversation_id, str)
        else None,
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

    return AgentSession(
        session_id=session_id,
        project_root=project_root,
        history=_normalize_history_entries(value.get("history")),
        messages=_normalize_messages(value.get("messages")),
        tool_memory=_normalize_tool_memory(value.get("tool_memory")),
        recent_selected_targets=_normalize_string_list(
            value.get("recent_selected_targets")
        ),
        activity_label=(
            value["activity_label"]
            if isinstance(value.get("activity_label"), str)
            and value.get("activity_label")
            else "Ready"
        ),
        error=value.get("error") if isinstance(value.get("error"), str) else None,
        run_started_at=(
            float(value["run_started_at"])
            if isinstance(value.get("run_started_at"), (int, float))
            else None
        ),
        last_response_id=value.get("last_response_id")
        if isinstance(value.get("last_response_id"), str)
        else None,
        conversation_id=value.get("conversation_id")
        if isinstance(value.get("conversation_id"), str)
        else None,
        skill_state=dict(value["skill_state"])
        if isinstance(value.get("skill_state"), dict)
        else {},
        created_at=created_at,
        updated_at=updated_at,
    )


def persist_sessions_state() -> None:
    """Persist durable session state to the agent SQLite database."""
    with sessions_lock:
        serialized_sessions = [
            _serialize_session_state(session) for session in sessions_by_id.values()
        ]

    try:
        from atopile.model.sqlite import AgentSessions

        AgentSessions.init_db()
        AgentSessions.upsert_many(serialized_sessions)
    except Exception:
        log.exception("Failed to persist agent session state")


def _load_sessions_state() -> None:
    try:
        from atopile.model.sqlite import AgentSessions

        AgentSessions.init_db()
        raw_sessions = AgentSessions.load_all()
    except Exception:
        log.exception("Failed to read persisted agent session state from database")
        return

    if not isinstance(raw_sessions, list):
        return

    restored: dict[str, AgentSession] = {}
    for raw_session in raw_sessions:
        session = _deserialize_session_state(raw_session)
        if session is None:
            continue
        session.active_run_id = None
        session.run_started_at = None
        if session.activity_label != "Ready":
            session.activity_label = "Ready"
        session.error = None
        for message in session.messages:
            if not bool(message.get("pending")):
                continue
            message["pending"] = False
            message["activity"] = "Interrupted"
            if isinstance(message.get("content"), str) and message["content"]:
                continue
            message["content"] = "Run interrupted before completion."
        restored[session.session_id] = session

    if not restored:
        return

    with sessions_lock:
        sessions_by_id.clear()
        sessions_by_id.update(restored)

    log.info("Restored %d persisted agent sessions", len(restored))


def cleanup_finished_runs(
    max_age_seconds: float = DEFAULT_RUN_RETENTION_SECONDS,
) -> None:
    now = time.time()
    to_delete: list[str] = []

    with runs_lock:
        for run_id, run in runs_by_id.items():
            if run.status == RUN_STATUS_RUNNING:
                continue
            if (now - run.updated_at) <= max_age_seconds:
                continue
            to_delete.append(run_id)

        for run_id in to_delete:
            runs_by_id.pop(run_id, None)


def normalize_running_run_state(run: AgentRun) -> AgentRun:
    """Repair stale running runs when their task is already done."""
    if run.status != RUN_STATUS_RUNNING:
        return run
    task = run.task
    if task is None or not task.done():
        return run

    run.status = RUN_STATUS_FAILED
    run.error = ERROR_RUN_TASK_ENDED
    run.updated_at = time.time()

    if task.cancelled():
        run.error = ERROR_CANCELLED
    else:
        try:
            exc = task.exception()
        except Exception as task_error:
            exc = task_error
        if exc is not None:
            run.error = f"Run task failed: {exc}"

    return run


def _new_message_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def append_session_message(
    session: AgentSession,
    *,
    role: str,
    content: str,
    message_id: str | None = None,
    pending: bool = False,
    activity: str | None = None,
    tool_traces: list[dict[str, Any]] | None = None,
    checklist: dict[str, Any] | None = None,
    design_questions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message = UiAgentMessageData(
        id=message_id or _new_message_id(role),
        role=role,
        content=content,
        pending=pending,
        activity=activity,
        tool_traces=tool_traces or [],
        checklist=checklist,
        design_questions=design_questions,
    ).model_dump(mode="json")
    session.messages.append(message)
    session.updated_at = time.time()
    return message


def get_run_assistant_message(
    session: AgentSession,
    run_id: str,
) -> dict[str, Any] | None:
    target_id = f"{run_id}-assistant"
    for message in session.messages:
        if message.get("id") == target_id:
            return message
    return None


def start_run_session_state(session: AgentSession, run: AgentRun) -> None:
    append_session_message(
        session,
        role="user",
        content=run.message,
        message_id=f"{run.run_id}-user",
    )
    append_session_message(
        session,
        role="assistant",
        content="Thinking...",
        message_id=f"{run.run_id}-assistant",
        pending=True,
        activity="Planning",
        tool_traces=[],
    )
    session.activity_label = "Planning"
    session.error = None
    session.run_started_at = run.created_at
    session.updated_at = time.time()


def add_run_guidance_message(
    session: AgentSession,
    *,
    run_id: str,
    content: str,
    activity_label: str,
    pending_content: str,
) -> None:
    append_session_message(session, role="user", content=content)
    pending = get_run_assistant_message(session, run_id)
    if pending is not None:
        pending["content"] = pending_content
        pending["activity"] = activity_label
        pending["pending"] = True
    session.activity_label = activity_label
    session.error = None
    session.updated_at = time.time()


def request_run_stop(session: AgentSession, run_id: str) -> None:
    pending = get_run_assistant_message(session, run_id)
    if pending is not None:
        pending["content"] = "Stopping..."
        pending["activity"] = "Stopping"
        pending["pending"] = True
    session.activity_label = "Stopping"
    session.error = None
    session.updated_at = time.time()


def record_agent_action_error(
    session: AgentSession,
    *,
    action: str,
    error: str,
    run_id: str | None = None,
    request_message: str | None = None,
) -> None:
    if action == "agent.createRun" and request_message:
        append_session_message(session, role="user", content=request_message)
        append_session_message(
            session,
            role="assistant",
            content=f"Request failed: {error}",
            activity="Errored",
        )
        session.activity_label = "Errored"
    elif action == "agent.cancelRun":
        append_session_message(
            session,
            role="system",
            content=f"Stop failed: {error}",
        )
    elif action == "agent.steerRun":
        append_session_message(
            session,
            role="system",
            content=f"Steering failed: {error}",
        )
    elif action == "agent.interruptRun":
        append_session_message(
            session,
            role="system",
            content=f"Interrupt failed: {error}",
        )
    pending = get_run_assistant_message(session, run_id) if run_id else None
    if pending is not None and action == "agent.createRun":
        pending["content"] = f"Request failed: {error}"
        pending["activity"] = "Errored"
        pending["pending"] = False
    session.error = error
    session.updated_at = time.time()


def _compact_path(path: str) -> str:
    normalized = path.replace("\\", "/").replace("./", "").strip("/")
    if len(normalized) <= 44:
        return normalized
    segments = [segment for segment in normalized.split("/") if segment]
    if len(segments) <= 2:
        return f"...{normalized[-41:]}"
    return f".../{'/'.join(segments[-2:])}"


def _activity_from_progress(payload: dict[str, Any]) -> str | None:
    summary = payload.get("activity_summary")
    if isinstance(summary, str) and summary:
        return summary
    phase = payload.get("phase")
    status_text = payload.get("status_text")
    detail_text = payload.get("detail_text")
    if phase in {"thinking", "compacting"}:
        if isinstance(status_text, str) and status_text:
            if isinstance(detail_text, str) and detail_text:
                return f"{status_text}: {detail_text[:36]}"
            return status_text
        return "Compacting context" if phase == "compacting" else "Thinking"
    if phase == "tool_start":
        name = payload.get("name")
        args = payload.get("args")
        if name == "project_read_file" and isinstance(args, dict):
            path = args.get("path")
            if isinstance(path, str) and path:
                return f"Reading {_compact_path(path)}"
        if name == "project_edit_file" and isinstance(args, dict):
            path = args.get("path")
            if isinstance(path, str) and path:
                return f"Editing {_compact_path(path)}"
        if isinstance(name, str) and name.startswith("build_"):
            return "Building"
        return "Working"
    if phase == "tool_end":
        trace = payload.get("trace")
        if isinstance(trace, dict):
            result = trace.get("result")
            if isinstance(result, dict):
                message = result.get("message")
                if isinstance(message, str) and message:
                    return message[:46]
        return "Working"
    if phase == "design_questions":
        return "Questions for you"
    if phase == "error":
        return "Errored"
    if phase == "stopped":
        return "Stopped"
    if phase == "done":
        return "Complete"
    return None


def apply_run_progress_to_session(
    session: AgentSession,
    *,
    run_id: str,
    payload: dict[str, Any],
) -> None:
    pending = get_run_assistant_message(session, run_id)
    if pending is None:
        return

    activity = _activity_from_progress(payload)
    checklist = (
        payload.get("checklist") if isinstance(payload.get("checklist"), dict) else None
    )
    phase = payload.get("phase")

    if checklist is not None:
        pending["checklist"] = checklist

    if phase == "thinking":
        if activity:
            pending["activity"] = activity
            session.activity_label = activity
        session.updated_at = time.time()
        return

    if phase == "tool_start":
        call_id = payload.get("call_id")
        name = payload.get("name")
        args = payload.get("args")
        if isinstance(call_id, str) and isinstance(name, str):
            traces = list(pending.get("toolTraces") or [])
            running_trace = {
                "callId": call_id,
                "name": name,
                "args": args if isinstance(args, dict) else {},
                "ok": True,
                "result": {"message": "running"},
                "running": True,
            }
            for index, trace in enumerate(traces):
                if trace.get("callId") == call_id:
                    traces[index] = running_trace
                    break
            else:
                traces.append(running_trace)
            pending["toolTraces"] = traces
        if activity:
            pending["content"] = f"{activity}..."
            pending["activity"] = activity
            session.activity_label = activity
        session.updated_at = time.time()
        return

    if phase == "tool_end":
        trace = payload.get("trace")
        if isinstance(trace, dict):
            call_id = payload.get("call_id")
            finished_trace = {
                **trace,
                "callId": call_id if isinstance(call_id, str) else None,
                "running": False,
            }
            traces = list(pending.get("toolTraces") or [])
            if isinstance(call_id, str):
                for index, current in enumerate(traces):
                    if current.get("callId") == call_id:
                        traces[index] = finished_trace
                        break
                else:
                    traces.append(finished_trace)
            else:
                traces.append(finished_trace)
            pending["toolTraces"] = traces
        if activity:
            pending["content"] = f"{activity}..."
            pending["activity"] = activity
            session.activity_label = activity
        session.updated_at = time.time()
        return

    if phase == "design_questions":
        questions = payload.get("questions")
        if isinstance(questions, list):
            pending["content"] = (
                payload["context"]
                if isinstance(payload.get("context"), str) and payload.get("context")
                else "Design questions"
            )
            pending["designQuestions"] = {
                "context": payload.get("context")
                if isinstance(payload.get("context"), str)
                else "",
                "questions": questions,
            }
            pending["pending"] = False
        if activity:
            pending["activity"] = activity
            session.activity_label = activity
        session.updated_at = time.time()
        return

    if phase in {"done", "stopped", "error"}:
        pending["pending"] = False
        if activity:
            pending["activity"] = activity
            session.activity_label = activity
        session.updated_at = time.time()


def finalize_run_success(
    session: AgentSession,
    *,
    run_id: str,
    response_payload: dict[str, Any],
    terminal_label: str,
) -> None:
    pending = get_run_assistant_message(session, run_id)
    if pending is not None:
        pending["content"] = str(response_payload.get("assistantMessage") or "")
        pending["pending"] = False
        pending["activity"] = terminal_label
        traces = response_payload.get("toolTraces")
        if isinstance(traces, list):
            pending["toolTraces"] = [
                {
                    **trace,
                    "running": False,
                }
                for trace in traces
                if isinstance(trace, dict)
            ]
    session.activity_label = terminal_label
    session.error = None
    session.run_started_at = None
    session.updated_at = time.time()


def finalize_run_error(session: AgentSession, *, run_id: str, error: str) -> None:
    pending = get_run_assistant_message(session, run_id)
    if pending is None:
        append_session_message(
            session,
            role="assistant",
            content=f"Request failed: {error}",
            activity="Errored",
        )
    else:
        pending["content"] = f"Request failed: {error}"
        pending["activity"] = "Errored"
        pending["pending"] = False
    session.activity_label = "Errored"
    session.error = error
    session.run_started_at = None
    session.updated_at = time.time()


def consume_run_steer_messages(run_id: str) -> list[str]:
    with runs_lock:
        run = runs_by_id.get(run_id)
        if run is None or not run.steer_messages:
            return []
        queued = list(run.steer_messages)
        run.steer_messages.clear()
        run.consumed_steer_messages.extend(queued)
        run.updated_at = time.time()
        return queued


def consume_run_interrupt_messages(run_id: str) -> list[str]:
    with runs_lock:
        run = runs_by_id.get(run_id)
        if run is None or not run.interrupt_messages:
            return []
        queued = list(run.interrupt_messages)
        run.interrupt_messages.clear()
        run.consumed_interrupt_messages.extend(queued)
        run.updated_at = time.time()
        return queued


def is_run_stop_requested(run_id: str) -> bool:
    with runs_lock:
        run = runs_by_id.get(run_id)
        return bool(run and run.stop_requested)


def reset_session_state(session: AgentSession, *, project_root: str) -> None:
    """Clear per-project session state when switching scopes."""
    session.project_root = project_root
    session.history = []
    session.messages = []
    session.tool_memory = {}
    session.active_run_id = None
    session.activity_label = "Ready"
    session.error = None
    session.run_started_at = None
    session.last_response_id = None
    session.conversation_id = None
    session.skill_state = {}
    session.updated_at = time.time()


def ensure_session_idle(session: AgentSession) -> AgentRun | None:
    """Return the active run if still running, otherwise clear stale active IDs."""
    with runs_lock:
        active_run = runs_by_id.get(session.active_run_id or "")
        if active_run:
            active_run = normalize_running_run_state(active_run)

    if session.active_run_id and (
        active_run is None or active_run.status != RUN_STATUS_RUNNING
    ):
        session.active_run_id = None
        session.run_started_at = None
        if session.activity_label != "Errored":
            session.activity_label = "Ready"

    return active_run


def reserve_sync_turn(session: AgentSession) -> str | None:
    """Reserve exclusive sync execution for a session."""
    with session_execution_lock:
        active_run = ensure_session_idle(session)
        if active_run and active_run.status == RUN_STATUS_RUNNING:
            return None
        with sync_turns_lock:
            if session.session_id in sync_turns_by_session:
                return None
            token = uuid.uuid4().hex
            sync_turns_by_session[session.session_id] = token
            return token


def release_sync_turn(session_id: str, token: str | None) -> None:
    """Release a previously reserved sync execution slot."""
    if not token:
        return
    with sync_turns_lock:
        current = sync_turns_by_session.get(session_id)
        if current == token:
            sync_turns_by_session.pop(session_id, None)


def session_has_sync_turn(session_id: str) -> bool:
    with sync_turns_lock:
        return session_id in sync_turns_by_session


def reserve_background_run(session: AgentSession, run: AgentRun) -> bool:
    """Reserve background execution for a session and register the run atomically."""
    with session_execution_lock:
        active_run = ensure_session_idle(session)
        if active_run and active_run.status == RUN_STATUS_RUNNING:
            return False
        if session_has_sync_turn(session.session_id):
            return False
        with runs_lock:
            runs_by_id[run.run_id] = run
        session.active_run_id = run.run_id
        session.recent_selected_targets = list(run.selected_targets)
        return True


_load_sessions_state()
