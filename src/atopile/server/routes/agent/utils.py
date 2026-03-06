"""Execution/logging helpers for agent route modules."""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from typing import Any

from atopile.dataclasses import AgentEventRow, AppContext
from atopile.server.agent import AgentRunner, mediator
from atopile.server.agent.activity_summary import ActivitySummarizer
from atopile.server.agent.config import AgentConfig
from atopile.server.agent.execution_context import AgentExecutionContext
from atopile.server.agent.provider import OpenAIProvider
from atopile.server.agent.registry import ToolRegistry
from atopile.server.agent.runner import TraceCallback
from atopile.server.events import get_event_bus

from .models import (
    ASSISTANT_ROLE,
    ERROR_SESSION_EXPIRED,
    EVENT_AGENT_PROGRESS,
    EVENT_RUN_COMPLETED,
    EVENT_RUN_FAILED,
    EVENT_RUN_INTERRUPT_CONSUMED,
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
    AgentSession,
    SendMessageResponse,
    ToolTraceResponse,
    session_not_found_detail,
)
from .state import (
    consume_run_interrupt_messages,
    consume_run_steer_messages,
    is_run_stop_requested,
    persist_sessions_state,
    runs_by_id,
    runs_lock,
    sessions_by_id,
    sessions_lock,
)

_PROGRESS_DISABLE_VALUES = {"0", "false", "no", "off"}

_agent_logs_db_initialized = False
_config = AgentConfig.from_env()
orchestrator = AgentRunner(
    config=_config,
    provider=OpenAIProvider(config=_config),
    registry=ToolRegistry(),
)
activity_summarizer = ActivitySummarizer(config=_config)

log = logging.getLogger(__name__)

_ERROR_EVENTS = {
    "turn_failed",
    "run_failed",
}

_CHAIN_INTEGRITY_ERROR_SNIPPETS = (
    "No tool output found for function call",
    "previous_response_id",
    "Could not find response",
    "response not found",
)


def _ensure_agent_logs_db() -> None:
    """Lazily initialize the agent_logs DB (safe to call multiple times)."""
    global _agent_logs_db_initialized
    if _agent_logs_db_initialized:
        return
    try:
        from atopile.model.sqlite import AgentLogs, MessageLog

        AgentLogs.init_db()
        MessageLog.init_db()
        _agent_logs_db_initialized = True
    except Exception:
        log.exception("Failed to initialize agent_logs database")


def log_agent_event(event: str, payload: dict[str, Any]) -> None:
    """Append a structured agent event to the SQLite log."""
    _ensure_agent_logs_db()

    timestamp = datetime.now(timezone.utc).isoformat()
    session_id = str(payload.get("session_id", ""))
    run_id = payload.get("run_id")
    phase = payload.get("phase")
    tool_name = payload.get("name") or payload.get("tool_name")
    project_root = payload.get("project_root")
    step_kind = payload.get("step_kind")
    loop = payload.get("loop")
    tool_index = payload.get("tool_index")
    tool_count = payload.get("tool_count")
    call_id = payload.get("call_id")
    item_id = payload.get("item_id")
    model = payload.get("model")
    response_id = payload.get("response_id")
    previous_response_id = payload.get("previous_response_id")
    input_tokens = payload.get("input_tokens")
    output_tokens = payload.get("output_tokens")
    total_tokens = payload.get("total_tokens")
    reasoning_tokens = payload.get("reasoning_tokens")
    cached_input_tokens = payload.get("cached_input_tokens")
    duration_ms = payload.get("duration_ms")
    level = "ERROR" if event in _ERROR_EVENTS else "INFO"

    summary = None
    for key in ("status_text", "detail_text", "error", "reason", "message"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            summary = val.strip()[:200]
            break

    try:
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        payload_json = "{}"

    entry = AgentEventRow(
        session_id=session_id,
        run_id=str(run_id) if run_id else None,
        timestamp=timestamp,
        event=event,
        level=level,
        phase=str(phase) if phase else None,
        tool_name=str(tool_name) if tool_name else None,
        project_root=str(project_root) if project_root else None,
        summary=summary,
        step_kind=str(step_kind) if step_kind else None,
        loop=int(loop) if isinstance(loop, int | float) else None,
        tool_index=int(tool_index) if isinstance(tool_index, int | float) else None,
        tool_count=int(tool_count) if isinstance(tool_count, int | float) else None,
        call_id=str(call_id) if call_id else None,
        item_id=str(item_id) if item_id else None,
        model=str(model) if model else None,
        response_id=str(response_id) if response_id else None,
        previous_response_id=(
            str(previous_response_id) if previous_response_id else None
        ),
        input_tokens=(
            int(input_tokens) if isinstance(input_tokens, int | float) else None
        ),
        output_tokens=(
            int(output_tokens) if isinstance(output_tokens, int | float) else None
        ),
        total_tokens=(
            int(total_tokens) if isinstance(total_tokens, int | float) else None
        ),
        reasoning_tokens=(
            int(reasoning_tokens) if isinstance(reasoning_tokens, int | float) else None
        ),
        cached_input_tokens=(
            int(cached_input_tokens)
            if isinstance(cached_input_tokens, int | float)
            else None
        ),
        duration_ms=int(duration_ms) if isinstance(duration_ms, int | float) else None,
        payload=payload_json,
    )

    try:
        from atopile.model.sqlite import AgentLogs

        AgentLogs.append_chunk([entry])
    except Exception:
        log.exception("Failed to append agent event to SQLite")


def is_chain_integrity_error(error: str) -> bool:
    return any(snippet in error for snippet in _CHAIN_INTEGRITY_ERROR_SNIPPETS)


def invalidate_session_response_chain(session: AgentSession) -> None:
    session.last_response_id = None
    session.conversation_id = None
    session.updated_at = time.time()


async def run_turn_with_chain_recovery(
    *,
    session: AgentSession,
    ctx: AppContext,
    project_root: str,
    history: list[dict[str, str]],
    user_message: str,
    session_id: str,
    run_id: str | None,
    selected_targets: list[str] | None,
    prior_skill_state: dict[str, Any] | None,
    tool_memory: dict[str, dict[str, Any]],
    progress_callback: Any = None,
    consume_steering_messages: Any = None,
    consume_interrupt_messages: Any = None,
    stop_requested: Any = None,
    trace_callback: TraceCallback | None = None,
) -> Any:
    """Retry once from local history when the provider response chain is stale."""
    run_ctx = AgentExecutionContext(
        **copy.copy(ctx).__dict__,
        agent_session_id=session_id,
        agent_run_id=run_id,
    )
    try:
        return await orchestrator.run_turn(
            ctx=run_ctx,
            project_root=project_root,
            history=history,
            user_message=user_message,
            session_id=session_id,
            run_id=run_id or "",
            selected_targets=selected_targets,
            previous_response_id=session.last_response_id,
            prior_skill_state=prior_skill_state,
            tool_memory=tool_memory,
            progress_callback=progress_callback,
            consume_steering_messages=consume_steering_messages,
            consume_interrupt_messages=consume_interrupt_messages,
            stop_requested=stop_requested,
            trace_callback=trace_callback,
        )
    except Exception as exc:
        if not is_chain_integrity_error(str(exc)) or not session.last_response_id:
            raise

        log.warning(
            "Invalidating stale response chain for session %s and retrying "
            "from local history",
            session_id,
        )
        invalidate_session_response_chain(session)

        return await orchestrator.run_turn(
            ctx=run_ctx,
            project_root=project_root,
            history=history,
            user_message=user_message,
            session_id=session_id,
            run_id=run_id or "",
            selected_targets=selected_targets,
            previous_response_id=None,
            prior_skill_state=prior_skill_state,
            tool_memory=tool_memory,
            progress_callback=progress_callback,
            consume_steering_messages=consume_steering_messages,
            consume_interrupt_messages=consume_interrupt_messages,
            stop_requested=stop_requested,
            trace_callback=trace_callback,
        )


def _should_log_run_progress() -> bool:
    raw = os.getenv("ATOPILE_AGENT_LOG_RUN_PROGRESS", "1").strip().lower()
    return raw not in _PROGRESS_DISABLE_VALUES


def build_run_trace_callback(
    *,
    session_id: str,
    run_id: str,
    project_root: str,
) -> TraceCallback:
    """Return a trace callback that writes to the agent SQLite log."""

    async def _trace(event: str, payload: dict[str, Any]) -> None:
        trace_payload = {
            "session_id": session_id,
            "run_id": run_id,
            "project_root": project_root,
            "name": payload.get("name"),
            "phase": "trace",
            "tool_name": payload.get("name"),
            **payload,
        }
        await asyncio.to_thread(log_agent_event, f"trace.{event}", trace_payload)

    return _trace


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
        "step_kind",
        "loop",
        "tool_index",
        "tool_count",
        "call_id",
        "name",
        "item_id",
        "model",
        "response_id",
        "previous_response_id",
        "reason",
    ):
        value = payload.get(key)
        if value is not None:
            summary[key] = value

    for key in (
        "duration_ms",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "reasoning_tokens",
        "cached_input_tokens",
        "model_call_count",
        "model_duration_ms",
        "tool_duration_ms",
        "decision_duration_ms",
        "checklist_remaining",
    ):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            summary[key] = int(value)

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
    steering_messages: list[str] | None,
    result: Any,
    mode: str,
    run_id: str | None = None,
) -> SendMessageResponse:
    """Update session state and build the HTTP response payload."""
    session.history.append({"role": USER_ROLE, "content": user_message})
    for steering_message in steering_messages or []:
        if steering_message.strip():
            session.history.append({"role": USER_ROLE, "content": steering_message})
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

    log_agent_event(
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
            "tool_traces": [trace.model_dump() for trace in response.tool_traces],
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
    activity_summary = await activity_summarizer.summarize(
        session_id=session_id,
        run_id=run_id,
        project_root=project_root,
        payload=payload,
    )
    event_payload: dict[str, Any] = {
        "session_id": session_id,
        "project_root": project_root,
        **payload,
    }
    if activity_summary:
        event_payload["activity_summary"] = activity_summary
    if run_id:
        event_payload["run_id"] = run_id
    await get_event_bus().emit(EVENT_AGENT_PROGRESS, event_payload)


def inject_build_completed_steering(
    project_root: str,
    build_id: str,
    target: str,
    status: str,
    warnings: int,
    errors: int,
    error: str | None,
    elapsed_seconds: float,
) -> bool:
    """Inject build-completion steering into any active run for a project."""
    parts = [f"[build completed] target={target} status={status}"]
    if elapsed_seconds:
        parts.append(f"elapsed={elapsed_seconds:.1f}s")
    if warnings:
        parts.append(f"warnings={warnings}")
    if errors:
        parts.append(f"errors={errors}")
    if error:
        short_error = error if len(error) <= 300 else error[:300] + "..."
        parts.append(f"error: {short_error}")
    parts.append(f"build_id={build_id}")
    if status.lower() in ("failed", "error"):
        parts.append("Use build_logs_search with this build_id to see the full error.")
    message = " | ".join(parts)

    with runs_lock:
        for run in runs_by_id.values():
            if run.status == RUN_STATUS_RUNNING and run.project_root == project_root:
                run.steer_messages.append(message)
                run.updated_at = time.time()
                log.info(
                    "Injected build-completed steering for run=%s build=%s",
                    run.run_id,
                    build_id,
                )
                return True
    return False


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

        log_agent_event(
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
            log_agent_event(
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
            log_agent_event(
                EVENT_RUN_STEER_CONSUMED,
                {
                    "run_id": run_id,
                    "session_id": session_id,
                    "project_root": run.project_root,
                    "count": len(queued),
                },
            )
        return queued

    def _consume_interrupt_messages() -> list[str]:
        queued = consume_run_interrupt_messages(run_id)
        if queued:
            log_agent_event(
                EVENT_RUN_INTERRUPT_CONSUMED,
                {
                    "run_id": run_id,
                    "session_id": session_id,
                    "project_root": run.project_root,
                    "count": len(queued),
                },
            )
        return queued

    trace_callback = build_run_trace_callback(
        session_id=session_id,
        run_id=run_id,
        project_root=run.project_root,
    )

    try:
        result = await run_turn_with_chain_recovery(
            session=session,
            ctx=ctx,
            project_root=run.project_root,
            history=list(session.history),
            user_message=run.message,
            session_id=session_id,
            run_id=run_id,
            selected_targets=run.selected_targets,
            prior_skill_state=session.skill_state,
            tool_memory=session.tool_memory,
            progress_callback=_emit_progress,
            consume_steering_messages=_consume_steering_messages,
            consume_interrupt_messages=_consume_interrupt_messages,
            stop_requested=lambda: is_run_stop_requested(run_id),
            trace_callback=trace_callback,
        )
    except asyncio.CancelledError:
        with runs_lock:
            cancelled = runs_by_id.get(run_id)
            if cancelled and cancelled.status == RUN_STATUS_RUNNING:
                cancelled.status = RUN_STATUS_CANCELLED
                cancelled.error = "Cancelled"
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
            if current:
                if current.active_run_id == run_id:
                    current.active_run_id = None
                if is_chain_integrity_error(str(exc)):
                    invalidate_session_response_chain(current)
                current.history.append({"role": USER_ROLE, "content": run.message})
                current.history.append(
                    {
                        "role": ASSISTANT_ROLE,
                        "content": (
                            f"[Run failed: {str(exc)[:200]}. "
                            "I was working on this but hit an error. "
                            "Please continue where I left off.]"
                        ),
                    }
                )

        persist_sessions_state()
        log_agent_event(
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

            log_agent_event(
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
            steering_messages_for_history: list[str] = []
            if latest is not None:
                steering_messages_for_history.extend(latest.consumed_steer_messages)
                steering_messages_for_history.extend(latest.steer_messages)
                latest.consumed_steer_messages.clear()
                latest.steer_messages.clear()
                latest.consumed_interrupt_messages.clear()
                latest.interrupt_messages.clear()
                latest.stop_requested = False

        response = build_send_message_response(
            session=active_session,
            user_message=run.message,
            steering_messages=steering_messages_for_history,
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

    log_agent_event(
        EVENT_RUN_COMPLETED,
        {
            "run_id": run_id,
            "session_id": session_id,
            "project_root": run.project_root,
            "tool_trace_count": len(response.tool_traces),
        },
    )


# ----------------------------------------
#                 Tests
# ----------------------------------------


class TestAgentLogging:
    def test_log_agent_event_persists_structured_telemetry_fields(
        self, monkeypatch, tmp_path
    ) -> None:
        db_path = tmp_path / "agent_logs.db"

        monkeypatch.setattr("atopile.model.sqlite.AGENT_LOGS_DB", db_path)
        monkeypatch.setattr(sys.modules[__name__], "_agent_logs_db_initialized", False)

        log_agent_event(
            "run_progress",
            {
                "session_id": "session_1",
                "run_id": "run_1",
                "project_root": "/tmp/project",
                "phase": "thinking",
                "step_kind": "model_response_received",
                "loop": 3,
                "tool_index": 1,
                "tool_count": 2,
                "call_id": "call_123",
                "item_id": "pkg-mcu",
                "model": "gpt-5.4",
                "response_id": "resp_123",
                "previous_response_id": "resp_122",
                "input_tokens": 1000,
                "output_tokens": 250,
                "total_tokens": 1250,
                "reasoning_tokens": 200,
                "cached_input_tokens": 800,
                "duration_ms": 3210,
                "status_text": "Model response received",
                "detail_text": "2 tool call(s), phase=unspecified",
            },
        )

        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT event, phase, step_kind, loop, tool_index, tool_count, call_id,
                       item_id, model, response_id, previous_response_id,
                       input_tokens, output_tokens, total_tokens,
                       reasoning_tokens, cached_input_tokens, duration_ms
                FROM agent_events
                """
            ).fetchone()

        assert row == (
            "run_progress",
            "thinking",
            "model_response_received",
            3,
            1,
            2,
            "call_123",
            "pkg-mcu",
            "gpt-5.4",
            "resp_123",
            "resp_122",
            1000,
            250,
            1250,
            200,
            800,
            3210,
        )

    def test_run_turn_with_chain_recovery_retries_without_last_response_id(
        self, monkeypatch
    ) -> None:
        session = AgentSession(
            session_id="session_1",
            project_root="/tmp/project",
            last_response_id="resp_bad",
        )
        calls: list[object] = []

        async def fake_run_turn(**kwargs: object):
            calls.append(kwargs.get("previous_response_id"))
            if len(calls) == 1:
                raise RuntimeError(
                    "Model API request failed (400): No tool output found for "
                    "function call call_123."
                )
            return {"ok": True}

        monkeypatch.setattr(orchestrator, "run_turn", fake_run_turn)

        import asyncio

        result = asyncio.run(
            run_turn_with_chain_recovery(
                session=session,
                ctx=AppContext(workspace_paths=[]),
                project_root="/tmp/project",
                history=[],
                user_message="continue",
                session_id=session.session_id,
                run_id="run_1",
                selected_targets=[],
                prior_skill_state=None,
                tool_memory={},
            )
        )

        assert result == {"ok": True}
        assert calls == ["resp_bad", None]
        assert session.last_response_id is None
