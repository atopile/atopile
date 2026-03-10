"""Stateful session/run storage for agent routes."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .models import (
    ERROR_CANCELLED,
    ERROR_RUN_TASK_ENDED,
    RUN_STATUS_FAILED,
    RUN_STATUS_RUNNING,
    AgentRun,
    AgentSession,
)

SESSION_STATE_VERSION = 1
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

log = logging.getLogger(__name__)


def _get_agent_session_state_path() -> Path:
    from faebryk.libs.paths import get_log_dir

    override = os.getenv("ATOPILE_AGENT_SESSION_STATE_PATH")
    if override and override.strip():
        return Path(override).expanduser()
    return get_log_dir() / "agent_sessions_state.json"


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
        "scope_root": session.scope_root,
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
    scope_root = value.get("scope_root")
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
        scope_root=scope_root
        if isinstance(scope_root, str) and scope_root
        else project_root,
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


def reset_session_state(
    session: AgentSession,
    *,
    project_root: str,
    scope_root: str | None = None,
) -> None:
    """Clear per-project session state when switching scopes."""
    session.project_root = project_root
    session.scope_root = scope_root or project_root
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
