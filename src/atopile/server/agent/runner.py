"""Agent runner — the core while(tool_calls) loop."""

from __future__ import annotations

import inspect
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from atopile.dataclasses import AppContext
from atopile.server.agent import tools as _legacy_tools
from atopile.server.agent.circuit_breaker import CircuitBreaker
from atopile.server.agent.config import AgentConfig
from atopile.server.agent.context import build_initial_user_message, build_system_prompt
from atopile.server.agent.conversation_log import ConversationLog
from atopile.server.agent.orchestrator_helpers import (
    _build_function_call_outputs_for_model,
    _build_steering_inputs_for_model,
    _consume_steering_updates,
    _limit_tool_output_for_model,
    _sanitize_tool_output_for_model,
    _summarize_function_call_for_trace,
    _summarize_tool_result_for_trace,
    _to_trace_preview,
)
from atopile.server.agent.provider import LLMProvider, LLMResponse, OpenAIProvider
from atopile.server.agent.registry import ToolRegistry

log = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]
SteeringMessagesCallback = Callable[[], list[str]]
MessageCallback = Callable[[dict[str, Any]], Awaitable[None] | None]
TraceCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


@dataclass
class ToolTrace:
    name: str
    args: dict[str, Any]
    ok: bool
    result: dict[str, Any]


@dataclass
class AgentTurnResult:
    text: str
    tool_traces: list[ToolTrace]
    model: str
    response_id: str | None = None
    skill_state: dict[str, Any] = field(default_factory=dict)
    context_metrics: dict[str, Any] = field(default_factory=dict)


def _apply_project_edit_remaps(
    arguments: dict[str, Any],
    remaps: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Re-map hashline anchors when the model uses stale names."""
    normalized_remaps = {
        str(k).strip().lower(): str(v).strip()
        for k, v in remaps.items()
        if str(k).strip() and str(v).strip()
    }
    if not normalized_remaps:
        return arguments, False

    raw_edits = arguments.get("edits")
    if not isinstance(raw_edits, list):
        return arguments, False

    changed = False
    updated_arguments = dict(arguments)
    updated_edits: list[dict[str, Any]] = []

    for raw_edit in raw_edits:
        if not isinstance(raw_edit, dict):
            continue
        edit = dict(raw_edit)

        for key_name, anchor_keys in [
            ("set_line", ["anchor"]),
            ("replace_lines", ["start_anchor", "end_anchor"]),
            ("insert_after", ["anchor"]),
        ]:
            sub = edit.get(key_name)
            if not isinstance(sub, dict):
                continue
            updated_sub = dict(sub)
            for ak in anchor_keys:
                raw_anchor = updated_sub.get(ak)
                if not isinstance(raw_anchor, str):
                    continue
                prefix, sep, suffix = raw_anchor.partition("|")
                mapped = normalized_remaps.get(prefix.strip().lower())
                if mapped:
                    updated_sub[ak] = f"{mapped}|{suffix}" if sep else mapped
                    changed = True
            edit[key_name] = updated_sub

        updated_edits.append(edit)

    if not changed:
        return arguments, False
    updated_arguments["edits"] = updated_edits
    return updated_arguments, True


class AgentRunner:
    def __init__(
        self,
        config: AgentConfig,
        provider: LLMProvider,
        registry: ToolRegistry,
    ) -> None:
        self._config = config
        self._provider = provider
        self._registry = registry

    # ── Public API ────────────────────────────────────────────────────
    # Signature matches AgentOrchestrator.run_turn() exactly.

    async def run_turn(
        self,
        *,
        ctx: AppContext,
        project_root: str,
        history: list[dict[str, str]],
        user_message: str,
        selected_targets: list[str] | None = None,
        previous_response_id: str | None = None,
        tool_memory: dict[str, dict[str, Any]] | None = None,
        progress_callback: ProgressCallback | None = None,
        consume_steering_messages: SteeringMessagesCallback | None = None,
        message_callback: MessageCallback | None = None,
        trace_callback: TraceCallback | None = None,
    ) -> AgentTurnResult:
        _ = message_callback  # reserved for future multi-agent messaging
        cfg = self._config

        project_path = _legacy_tools.validate_tool_scope(project_root, ctx)
        selected = selected_targets or []
        include_primer = previous_response_id is None and len(history) == 0

        # Build system prompt + skill state
        instructions, skill_state = build_system_prompt(
            config=cfg,
            project_root=project_path,
            selected_targets=selected,
            include_session_primer=include_primer,
        )

        # Build initial input
        user_content = await build_initial_user_message(
            project_root=project_path,
            selected_targets=selected,
            user_message=user_message,
            context_max_chars=cfg.context_summary_max_chars,
            message_max_chars=cfg.user_message_max_chars,
        )
        history_for_model = history if previous_response_id is None else []
        request_input: list[dict[str, Any]] = list(history_for_model)
        request_input.append({"role": "user", "content": user_content})

        # Consume any early steering
        steering_inputs = self._collect_steering(consume_steering_messages)
        if steering_inputs:
            request_input.extend(steering_inputs)

        tool_defs = self._registry.definitions()

        # Conversation log for debugging
        conv_log = ConversationLog(
            run_id=str(uuid.uuid4()),
            session_id="",
        )
        breaker = CircuitBreaker()
        traces: list[ToolTrace] = []
        loops = 0
        last_response_id = previous_response_id
        started_at = time.monotonic()
        telemetry: dict[str, Any] = {"api_retry_count": 0, "compaction_events": []}

        active_trace = trace_callback if cfg.trace_enabled else None
        await self._emit_trace(
            active_trace,
            "turn_started",
            {
                "model": cfg.model,
                "project_root": str(project_path),
                "selected_targets": list(selected),
                "history_items": len(history),
            },
        )

        # Initial LLM call
        await self._emit_progress(
            progress_callback,
            {
                "phase": "thinking",
                "status_text": "Planning",
                "detail_text": "Reviewing request and project context",
            },
        )
        response = await self._provider.complete(
            messages=request_input,
            instructions=instructions,
            tools=tool_defs,
            skill_state=skill_state,
            project_path=project_path,
            previous_response_id=previous_response_id,
        )
        last_response_id = response.id or last_response_id
        conv_log.record(
            "llm_response",
            text_len=len(response.text),
            tool_calls=len(response.tool_calls),
        )

        # ── Main loop ────────────────────────────────────────────────
        while loops < cfg.max_tool_loops:
            elapsed = time.monotonic() - started_at

            # Time budget check
            if elapsed >= cfg.max_turn_seconds:
                return self._stop(
                    reason="turn_time_budget_exceeded",
                    text=(
                        f"Stopped after exceeding the per-turn time budget "
                        f"({elapsed:.1f}s, {loops} loops, {len(traces)} tool calls)."
                    ),
                    traces=traces,
                    last_response_id=last_response_id,
                    skill_state=skill_state,
                    telemetry=telemetry,
                )

            loops += 1

            # No tool calls → check steering, then done
            if not response.tool_calls:
                steering = self._collect_steering(consume_steering_messages)
                if steering:
                    await self._emit_progress(
                        progress_callback,
                        {
                            "phase": "thinking",
                            "status_text": "Steering",
                            "detail_text": "Applying latest user guidance",
                        },
                    )
                    response = await self._provider.complete(
                        messages=steering,
                        instructions=instructions,
                        tools=tool_defs,
                        skill_state=skill_state,
                        project_path=project_path,
                        previous_response_id=last_response_id,
                    )
                    last_response_id = response.id or last_response_id
                    continue

                text = response.text or "No assistant response produced."
                await self._emit_trace(
                    active_trace,
                    "turn_completed",
                    {
                        "loop": loops,
                        "tool_calls_total": len(traces),
                        "response_id": response.id,
                    },
                )
                await self._emit_progress(
                    progress_callback,
                    {"phase": "done", "loop": loops, "tool_calls_total": len(traces)},
                )
                return AgentTurnResult(
                    text=text,
                    tool_traces=traces,
                    model=cfg.model,
                    response_id=last_response_id,
                    skill_state=skill_state,
                    context_metrics=telemetry,
                )

            # Execute tool calls
            outputs: list[dict[str, Any]] = []
            tool_count = len(response.tool_calls)
            for tool_index, call in enumerate(response.tool_calls, start=1):
                await self._emit_progress(
                    progress_callback,
                    {
                        "phase": "tool_start",
                        "loop": loops,
                        "tool_index": tool_index,
                        "tool_count": tool_count,
                        "call_id": call.id,
                        "name": call.name,
                        "args": call.arguments,
                    },
                )
                await self._emit_trace(
                    active_trace,
                    "tool_call_started",
                    {
                        "loop": loops,
                        "tool_index": tool_index,
                        "tool_count": tool_count,
                        "call_id": call.id,
                        "name": call.name,
                        "parsed_arguments": call.arguments,
                    },
                )

                args, result_payload, ok = await self._execute_tool(
                    tool_name=call.name,
                    raw_args=call.arguments_raw,
                    parsed_args=call.arguments,
                    project_path=project_path,
                    ctx=ctx,
                )

                trace = ToolTrace(name=call.name, args=args, ok=ok, result=result_payload)
                traces.append(trace)

                if ok:
                    breaker.record_success()
                else:
                    trip_msg = breaker.record_failure(
                        call.name, args, str(result_payload.get("error", ""))
                    )
                    if trip_msg:
                        result_payload["circuit_breaker"] = trip_msg
                        conv_log.record("circuit_breaker", tool=call.name, message=trip_msg)

                await self._emit_progress(
                    progress_callback,
                    {
                        "phase": "tool_end",
                        "loop": loops,
                        "tool_index": tool_index,
                        "tool_count": tool_count,
                        "call_id": call.id,
                        "trace": {
                            "name": call.name,
                            "args": args,
                            "ok": ok,
                            "result": result_payload,
                        },
                    },
                )
                await self._emit_trace(
                    active_trace,
                    "tool_call_completed",
                    {
                        "loop": loops,
                        "call_id": call.id,
                        "name": call.name,
                        "ok": ok,
                        "arguments": args,
                        "result": _summarize_tool_result_for_trace(
                            result_payload, max_chars=cfg.trace_preview_max_chars
                        ),
                    },
                )

                conv_log.record(
                    "tool_result",
                    tool=call.name,
                    ok=ok,
                    error=result_payload.get("error") if not ok else None,
                )

                # Build function call output for model
                outputs.extend(
                    _build_function_call_outputs_for_model(
                        call_id=call.id,
                        tool_name=call.name,
                        result_payload=_limit_tool_output_for_model(
                            _sanitize_tool_output_for_model(result_payload),
                            max_chars=cfg.tool_output_max_chars,
                        ),
                    )
                )

            # Append steering if available
            steering = self._collect_steering(consume_steering_messages)
            if steering:
                outputs.extend(steering)

            # Thinking progress
            await self._emit_progress(
                progress_callback,
                {
                    "phase": "thinking",
                    "status_text": "Reviewing tool results",
                    "detail_text": "Choosing next step",
                    "loop": loops,
                    "tool_calls_total": len(traces),
                },
            )

            # Next LLM call with tool results
            response = await self._provider.complete(
                messages=outputs,
                instructions=instructions,
                tools=tool_defs,
                skill_state=skill_state,
                project_path=project_path,
                previous_response_id=last_response_id,
            )
            last_response_id = response.id or last_response_id
            conv_log.record(
                "llm_response",
                text_len=len(response.text),
                tool_calls=len(response.tool_calls),
            )

        # Exhausted loop budget
        return self._stop(
            reason="too_many_tool_iterations",
            text="Stopped after too many tool iterations.",
            traces=traces,
            last_response_id=last_response_id,
            skill_state=skill_state,
            telemetry=telemetry,
        )

    # ── Private helpers ───────────────────────────────────────────────

    async def _execute_tool(
        self,
        *,
        tool_name: str,
        raw_args: str,
        parsed_args: dict[str, Any] | None,
        project_path: Path,
        ctx: AppContext,
    ) -> tuple[dict[str, Any], dict[str, Any], bool]:
        """Execute a tool call with auto-remap retry for project_edit_file."""
        args: dict[str, Any] = parsed_args if parsed_args is not None else {}
        ok = True
        try:
            if parsed_args is None:
                args = _legacy_tools.parse_tool_arguments(raw_args)
            result_payload = await self._registry.execute(
                tool_name, args, project_path, ctx
            )
        except Exception as exc:
            ok = False
            remaps = getattr(exc, "remaps", None)
            auto_remap_attempted = False

            # Auto-remap retry for project_edit_file
            if tool_name == "project_edit_file" and isinstance(remaps, dict):
                remapped_args, did_remap = _apply_project_edit_remaps(args, remaps)
                if did_remap:
                    auto_remap_attempted = True
                    try:
                        result_payload = await self._registry.execute(
                            tool_name, remapped_args, project_path, ctx
                        )
                        args = remapped_args
                        ok = True
                        if isinstance(result_payload, dict):
                            result_payload = dict(result_payload)
                            result_payload["auto_remap_retry"] = True
                    except Exception as remap_exc:
                        args = remapped_args
                        exc = remap_exc
                        remaps = getattr(remap_exc, "remaps", None)

            if not ok:
                result_payload = {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
                if auto_remap_attempted:
                    result_payload["auto_remap_retry"] = True
                if isinstance(remaps, dict):
                    result_payload["remaps"] = remaps
                mismatches = getattr(exc, "mismatches", None)
                if isinstance(mismatches, list):
                    result_payload["mismatches"] = [
                        {
                            "line": getattr(m, "line", None),
                            "expected": getattr(m, "expected", None),
                            "actual": getattr(m, "actual", None),
                        }
                        for m in mismatches
                    ]

        return args, result_payload, ok

    def _stop(
        self,
        *,
        reason: str,
        text: str,
        traces: list[ToolTrace],
        last_response_id: str | None,
        skill_state: dict[str, Any],
        telemetry: dict[str, Any],
    ) -> AgentTurnResult:
        return AgentTurnResult(
            text=text,
            tool_traces=traces,
            model=self._config.model,
            response_id=last_response_id,
            skill_state=skill_state,
            context_metrics=telemetry,
        )

    @staticmethod
    def _collect_steering(
        consume_steering_messages: SteeringMessagesCallback | None,
    ) -> list[dict[str, Any]]:
        return _build_steering_inputs_for_model(
            _consume_steering_updates(consume_steering_messages)
        )

    @staticmethod
    async def _emit_progress(
        callback: ProgressCallback | None,
        payload: dict[str, Any],
    ) -> None:
        if callback is None:
            return
        maybe = callback(payload)
        if inspect.isawaitable(maybe):
            await maybe

    @staticmethod
    async def _emit_trace(
        callback: TraceCallback | None,
        event: str,
        payload: dict[str, Any],
    ) -> None:
        if callback is None:
            return
        maybe = callback(event, payload)
        if inspect.isawaitable(maybe):
            await maybe
