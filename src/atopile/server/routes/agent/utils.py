"""Shared state and utility functions for agent route modules."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atopile.dataclasses import AppContext
from atopile.server.agent import AgentOrchestrator, mediator
from atopile.server.agent.orchestrator import TraceCallback
from atopile.server.events import get_event_bus
from faebryk.libs.paths import get_log_dir

from .models import (
    ASSISTANT_ROLE,
    ERROR_CANCELLED,
    ERROR_RUN_TASK_ENDED,
    ERROR_SESSION_EXPIRED,
    EVENT_AGENT_MESSAGE,
    EVENT_AGENT_PROGRESS,
    EVENT_RUN_COMPLETED,
    EVENT_RUN_FAILED,
    EVENT_RUN_PROGRESS,
    EVENT_RUN_STEER_CONSUMED,
    EVENT_TURN_COMPLETED,
    PHASE_ERROR,
    RUN_STATUS_CANCELLED,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_RUNNING,
    TURN_MODE_BACKGROUND,
    USER_ROLE,
    AgentRun,
    AgentSession,
    SendMessageResponse,
    ToolTraceResponse,
    session_not_found_detail,
)

SESSION_STATE_VERSION = 1
DEFAULT_MAX_PERSISTED_HISTORY = 160
MIN_PERSISTED_HISTORY = 20
MAX_PERSISTED_HISTORY = 2_000
DEFAULT_RUN_RETENTION_SECONDS = 3_600.0

_PROGRESS_DISABLE_VALUES = {"0", "false", "no", "off"}
_TRACE_DISABLE_VALUES = {"0", "false", "no", "off"}

sessions_by_id: dict[str, AgentSession] = {}
sessions_lock = threading.Lock()
runs_by_id: dict[str, AgentRun] = {}
runs_lock = threading.Lock()
_session_log_lock = threading.Lock()
_trace_log_lock = threading.Lock()
orchestrator = AgentOrchestrator()

log = logging.getLogger(__name__)


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


def _get_agent_trace_log_dir() -> Path:
    override = os.getenv("ATOPILE_AGENT_TRACE_LOG_DIR")
    if override and override.strip():
        return Path(override).expanduser()
    return get_log_dir() / "agent_traces"


def _build_agent_trace_log_path(*, session_id: str, run_id: str) -> Path:
    safe_session = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in session_id
    )
    safe_run = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in run_id)
    return _get_agent_trace_log_dir() / safe_session / f"{safe_run}.jsonl"


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
        tool_memory=_normalize_tool_memory(value.get("tool_memory")),
        recent_selected_targets=_normalize_string_list(
            value.get("recent_selected_targets")
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
    """Persist durable session state to disk."""
    with sessions_lock:
        serialized_sessions = [
            _serialize_session_state(session) for session in sessions_by_id.values()
        ]

    payload = {
        "version": SESSION_STATE_VERSION,
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
        session.active_run_id = None
        restored[session.session_id] = session

    if not restored:
        return

    with sessions_lock:
        sessions_by_id.clear()
        sessions_by_id.update(restored)

    log.info("Restored %d persisted agent sessions", len(restored))


def log_session_event(event: str, payload: dict[str, Any]) -> None:
    """Append a structured session event to the local JSONL log."""
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


def _should_log_run_progress() -> bool:
    raw = os.getenv("ATOPILE_AGENT_LOG_RUN_PROGRESS", "1").strip().lower()
    return raw not in _PROGRESS_DISABLE_VALUES


def _should_log_agent_traces() -> bool:
    raw = os.getenv("ATOPILE_AGENT_LOG_TRACE_EVENTS", "1").strip().lower()
    return raw not in _TRACE_DISABLE_VALUES


def _append_trace_event(
    *,
    trace_log_path: Path,
    session_id: str,
    run_id: str,
    project_root: str,
    event: str,
    payload: dict[str, Any],
) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "run_id": run_id,
        "project_root": project_root,
        "event": event,
        "payload": payload,
    }
    try:
        encoded = json.dumps(record, ensure_ascii=False, default=str)
        with _trace_log_lock:
            trace_log_path.parent.mkdir(parents=True, exist_ok=True)
            with trace_log_path.open("a", encoding="utf-8") as handle:
                handle.write(encoded + "\n")
    except Exception:
        log.exception("Failed to append agent trace event")


def build_run_trace_callback(
    *,
    session_id: str,
    run_id: str,
    project_root: str,
) -> tuple[TraceCallback | None, str | None]:
    if not _should_log_agent_traces():
        return None, None

    trace_log_path = _build_agent_trace_log_path(session_id=session_id, run_id=run_id)

    async def _trace(event: str, payload: dict[str, Any]) -> None:
        await asyncio.to_thread(
            _append_trace_event,
            trace_log_path=trace_log_path,
            session_id=session_id,
            run_id=run_id,
            project_root=project_root,
            event=event,
            payload=payload,
        )

    return _trace, str(trace_log_path)


def _truncate_log_text(value: Any, *, max_chars: int = 240) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 15].rstrip() + "...[truncated]"


def _summarize_progress_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in (
        "phase",
        "loop",
        "tool_index",
        "tool_count",
        "call_id",
        "name",
        "reason",
    ):
        value = payload.get(key)
        if value is not None:
            summary[key] = value

    status_text = _truncate_log_text(payload.get("status_text"), max_chars=120)
    if status_text:
        summary["status_text"] = status_text
    detail_text = _truncate_log_text(payload.get("detail_text"), max_chars=180)
    if detail_text:
        summary["detail_text"] = detail_text
    error_text = _truncate_log_text(payload.get("error"), max_chars=300)
    if error_text:
        summary["error"] = error_text

    total_tokens = payload.get("total_tokens")
    if isinstance(total_tokens, (int, float)):
        summary["total_tokens"] = int(total_tokens)

    trace = payload.get("trace")
    if isinstance(trace, dict):
        trace_summary: dict[str, Any] = {}
        name = trace.get("name")
        if isinstance(name, str) and name:
            trace_summary["name"] = name
        ok = trace.get("ok")
        if isinstance(ok, bool):
            trace_summary["ok"] = ok
        result = trace.get("result")
        if isinstance(result, dict):
            err = _truncate_log_text(result.get("error"), max_chars=180)
            if err:
                trace_summary["error"] = err
            if "truncated" in result:
                trace_summary["truncated"] = bool(result.get("truncated"))
        if trace_summary:
            summary["trace"] = trace_summary

    args = payload.get("args")
    if isinstance(args, dict):
        keys = sorted(str(key) for key in args.keys())
        if keys:
            summary["args_keys"] = keys[:20]

    return summary


def build_send_message_response(
    *,
    session: AgentSession,
    user_message: str,
    result: Any,
    mode: str,
    run_id: str | None = None,
) -> SendMessageResponse:
    """Update session state and build the HTTP response payload."""
    session.history.append({"role": USER_ROLE, "content": user_message})
    session.history.append({"role": ASSISTANT_ROLE, "content": result.text})
    session.tool_memory = mediator.update_tool_memory(
        session.tool_memory, result.tool_traces
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

    agent_messages = [
        message
        for message in getattr(result, "agent_messages", [])
        if isinstance(message, dict)
    ]

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

    log_session_event(
        EVENT_TURN_COMPLETED,
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
            "agent_message_count": len(agent_messages),
            "tool_traces": [trace.model_dump() for trace in response.tool_traces],
            "agent_messages": agent_messages,
            "last_response_id": session.last_response_id,
            "skill_state": session.skill_state,
            "context_metrics": getattr(result, "context_metrics", {}),
        },
    )
    return response


async def emit_agent_progress(
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
    await get_event_bus().emit(EVENT_AGENT_PROGRESS, event_payload)


async def emit_agent_message(
    *,
    session_id: str,
    project_root: str,
    run_id: str,
    message: dict[str, Any],
) -> None:
    await get_event_bus().emit(
        EVENT_AGENT_MESSAGE,
        {
            "session_id": session_id,
            "project_root": project_root,
            "run_id": run_id,
            "message": message,
        },
    )


def post_agent_run_message(run_id: str, message: dict[str, Any]) -> None:
    """Append a run message to in-memory inbox state."""
    if not isinstance(message, dict):
        return

    with runs_lock:
        run = runs_by_id.get(run_id)
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
            if isinstance(payload, dict):
                acked_id = payload.get("message_id")
                if isinstance(acked_id, str) and acked_id:
                    run.pending_acks.discard(acked_id)

        if (
            message.get("kind") == "intent_brief"
            and isinstance(message.get("payload"), dict)
            and not run.intent_snapshot
        ):
            run.intent_snapshot = dict(message["payload"])


def pull_agent_run_messages(
    run_id: str,
    *,
    agent_id: str,
    max_items: int = 50,
) -> list[dict[str, Any]]:
    """Read and advance the per-agent inbox cursor for a run."""
    max_items = max(1, min(max_items, 500))
    with runs_lock:
        run = runs_by_id.get(run_id)
        if run is None:
            return []

        cursor = run.inbox_cursor.get(agent_id, 0)
        if cursor < 0:
            cursor = 0
        messages = run.message_log[cursor : cursor + max_items]
        run.inbox_cursor[agent_id] = cursor + len(messages)
        run.updated_at = time.time()

    return [dict(message) for message in messages]


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


def consume_run_steer_messages(run_id: str) -> list[str]:
    with runs_lock:
        run = runs_by_id.get(run_id)
        if run is None or not run.steer_messages:
            return []
        queued = list(run.steer_messages)
        run.steer_messages.clear()
        run.updated_at = time.time()
    return queued


def reset_session_state(session: AgentSession, *, project_root: str) -> None:
    """Clear per-project session state when switching scopes."""
    session.project_root = project_root
    session.history = []
    session.tool_memory = {}
    session.active_run_id = None
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

    return active_run


async def run_turn_in_background(
    *,
    run_id: str,
    session_id: str,
    ctx: AppContext,
) -> None:
    with runs_lock:
        run = runs_by_id.get(run_id)
    if run is None:
        return

    with sessions_lock:
        session = sessions_by_id.get(session_id)
    if session is None:
        detail = session_not_found_detail(session_id)
        with runs_lock:
            missing = runs_by_id.get(run_id)
            if missing:
                missing.status = RUN_STATUS_FAILED
                missing.error = detail
                missing.updated_at = time.time()

        log_session_event(
            EVENT_RUN_FAILED,
            {
                "run_id": run_id,
                "session_id": session_id,
                "error": detail,
            },
        )
        return

    async def _emit_progress(payload: dict[str, Any]) -> None:
        await emit_agent_progress(
            session_id=session_id,
            project_root=run.project_root,
            run_id=run_id,
            payload=payload,
        )
        if _should_log_run_progress():
            log_session_event(
                EVENT_RUN_PROGRESS,
                {
                    "run_id": run_id,
                    "session_id": session_id,
                    "project_root": run.project_root,
                    **_summarize_progress_payload(payload),
                },
            )

    def _consume_steering_messages() -> list[str]:
        queued = consume_run_steer_messages(run_id)
        if queued:
            log_session_event(
                EVENT_RUN_STEER_CONSUMED,
                {
                    "run_id": run_id,
                    "session_id": session_id,
                    "project_root": run.project_root,
                    "count": len(queued),
                },
            )
        return queued

    async def _emit_message(message: dict[str, Any]) -> None:
        post_agent_run_message(run_id, message)
        await emit_agent_message(
            session_id=session_id,
            project_root=run.project_root,
            run_id=run_id,
            message=message,
        )

    trace_callback, trace_log_path = build_run_trace_callback(
        session_id=session_id,
        run_id=run_id,
        project_root=run.project_root,
    )
    if trace_log_path:
        log_session_event(
            EVENT_RUN_PROGRESS,
            {
                "run_id": run_id,
                "session_id": session_id,
                "project_root": run.project_root,
                "phase": "trace",
                "status_text": "Tracing enabled",
                "detail_text": trace_log_path,
            },
        )

    try:
        result = await orchestrator.run_turn(
            ctx=ctx,
            project_root=run.project_root,
            history=list(session.history),
            user_message=run.message,
            selected_targets=run.selected_targets,
            previous_response_id=session.last_response_id,
            tool_memory=session.tool_memory,
            progress_callback=_emit_progress,
            consume_steering_messages=_consume_steering_messages,
            message_callback=_emit_message,
            trace_callback=trace_callback,
        )
    except asyncio.CancelledError:
        with runs_lock:
            cancelled = runs_by_id.get(run_id)
            if cancelled and cancelled.status == RUN_STATUS_RUNNING:
                cancelled.status = RUN_STATUS_CANCELLED
                cancelled.error = ERROR_CANCELLED
                cancelled.updated_at = time.time()
        with sessions_lock:
            current = sessions_by_id.get(session_id)
            if current and current.active_run_id == run_id:
                current.active_run_id = None
        persist_sessions_state()
        return
    except Exception as exc:
        await _emit_progress({"phase": PHASE_ERROR, "error": str(exc)})

        with runs_lock:
            failed = runs_by_id.get(run_id)
            if failed:
                failed.status = RUN_STATUS_FAILED
                failed.error = str(exc)
                failed.updated_at = time.time()

        with sessions_lock:
            current = sessions_by_id.get(session_id)
            if current and current.active_run_id == run_id:
                current.active_run_id = None

        persist_sessions_state()
        log_session_event(
            EVENT_RUN_FAILED,
            {
                "run_id": run_id,
                "session_id": session_id,
                "project_root": run.project_root,
                "error": str(exc),
            },
        )
        return

    with sessions_lock:
        active_session = sessions_by_id.get(session_id)
        if active_session is None:
            with runs_lock:
                failed = runs_by_id.get(run_id)
                if failed:
                    failed.status = RUN_STATUS_FAILED
                    failed.error = ERROR_SESSION_EXPIRED
                    failed.updated_at = time.time()

            log_session_event(
                EVENT_RUN_FAILED,
                {
                    "run_id": run_id,
                    "session_id": session_id,
                    "project_root": run.project_root,
                    "error": ERROR_SESSION_EXPIRED,
                },
            )
            return

        with runs_lock:
            latest = runs_by_id.get(run_id)
            if latest is not None and latest.status != RUN_STATUS_RUNNING:
                return

        response = build_send_message_response(
            session=active_session,
            user_message=run.message,
            result=result,
            mode=TURN_MODE_BACKGROUND,
            run_id=run_id,
        )
        if active_session.active_run_id == run_id:
            active_session.active_run_id = None

    persist_sessions_state()

    with runs_lock:
        completed = runs_by_id.get(run_id)
        if completed:
            if completed.status != RUN_STATUS_RUNNING:
                return
            completed.status = RUN_STATUS_COMPLETED
            completed.error = None
            completed.response_payload = response.model_dump(by_alias=True)
            completed.updated_at = time.time()

    log_session_event(
        EVENT_RUN_COMPLETED,
        {
            "run_id": run_id,
            "session_id": session_id,
            "project_root": run.project_root,
            "tool_trace_count": len(response.tool_traces),
        },
    )


_load_sessions_state()
