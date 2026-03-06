"""Agent runner — the core while(tool_calls) loop."""

from __future__ import annotations

import copy
import inspect
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from atopile.dataclasses import AppContext
from atopile.server.agent import tools as _legacy_tools
from atopile.server.agent.checklist import VALID_TRANSITIONS, Checklist, ChecklistItem
from atopile.server.agent.message_log import (
    MSG_ACKNOWLEDGED,
    MSG_ACTIVE,
    MSG_DONE,
    MSG_PENDING,
    TrackedChecklistItem,
    TrackedMessage,
    build_pending_message_nudge,
)
from atopile.server.agent.circuit_breaker import CircuitBreaker
from atopile.server.agent.config import AgentConfig
from atopile.server.agent.context import build_initial_user_message, build_system_prompt
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

_CHECKLIST_TOOLS = frozenset(
    {"checklist_create", "checklist_update", "checklist_add_items"}
)
_MESSAGE_TOOLS = frozenset({"message_acknowledge", "message_log_query"})
_PLANNING_TOOLS = frozenset({"design_questions"})
_MANAGED_TOOLS = _CHECKLIST_TOOLS | _MESSAGE_TOOLS | _PLANNING_TOOLS

# Tools that represent productive work (reading, editing, building, etc.)
_WORK_TOOLS = frozenset(
    {
        "project_read_file",
        "project_edit_file",
        "project_list_files",
        "project_create_path",
        "build_run",
        "build_create",
        "build_rename",
        "parts_search",
        "parts_install",
        "packages_search",
        "packages_install",
        "datasheet_read",
        "design_diagnostics",
        "autolayout_request_screenshot",
        "layout_set_component_position",
        "layout_set_board_shape",
        "autolayout_run",
        "autolayout_status",
        "autolayout_fetch_to_layout",
        "web_search",
    }
)


_CHECKLIST_NUDGE_MSG = (
    "You've started doing real work (file edits, builds, searches) "
    "but don't have a checklist yet. Create one with checklist_create "
    "to track what you're doing, then continue working."
)

_MAX_CHECKLIST_NUDGES = 1


_MAX_MESSAGE_NUDGES = 2

_DESIGN_REVIEW_ITEMS = [
    ChecklistItem(
        id="review_requirements",
        description="Verify all user requirements are addressed in the design",
        criteria="Each stated requirement has corresponding ato implementation",
        source="review",
    ),
    ChecklistItem(
        id="review_build",
        description="Verify design builds successfully",
        criteria="Build passes or unsolvable issue clearly identified",
        source="review",
    ),
    ChecklistItem(
        id="review_interfaces",
        description="Verify standard library interfaces used where applicable",
        criteria="I2C, SPI, CAN, Ethernet, Power used instead of raw Electrical/ElectricLogic",
        source="review",
    ),
]

# If the model responds without tool calls to this many consecutive
# continuation/kickstart nudges, treat it as stuck and stop the loop.
_MAX_EMPTY_CONTINUATIONS = 5

# Sent when the model's text suggests it thinks tools are unavailable.
_REGROUND_TOOLS_MSG = (
    "You have FULL access to all tools listed in your function definitions. "
    "checklist_update, project_read_file, project_edit_file, build_run, "
    "and all other tools are available right now. "
    "Do not describe what you would do — call the tool directly. "
    "Start by calling checklist_update to mark the next item as 'doing', "
    "then execute it."
)

# Patterns in model text that indicate it thinks tools are unavailable.
_STUCK_TOOL_PATTERNS = (
    "missing tool",
    "cannot run",
    "can't run",
    "cannot call",
    "can't call",
    "unable to call",
    "unable to run",
    "cannot execute",
    "can't execute",
    "tool execution access",
    "no tool access",
    "blocked by",
    "don't have access to",
    "do not have access to",
)


def _summarize_model_preamble(text: str, *, max_chars: int = 180) -> str | None:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return None
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[: max_chars - 1].rstrip()}…"


def _build_turn_time_budget_stop_text(
    elapsed: float, loops: int, traces: list[ToolTrace]
) -> str:
    return (
        f"Stopped after exceeding the per-turn time budget "
        f"({elapsed:.1f}s, {loops} loops, {len(traces)} tool calls)."
    )


def _build_kickstart_msg(checklist: Any) -> str:
    """Build a forceful kickstart prompt when the model produces empty responses.

    Identifies the first non-terminal item and tells the model exactly what
    tool call to make next.
    """
    incomplete = checklist.incomplete_items() if checklist else []
    if not incomplete:
        return _REGROUND_TOOLS_MSG

    first = incomplete[0]
    return (
        f"Your previous response was empty — you MUST call a tool now.\n\n"
        f"Next checklist item: {first.id} — {first.description}\n\n"
        f'Step 1: Call checklist_update with item_id="{first.id}" and '
        f'status="doing"\n'
        f"Step 2: Call project_read_file or project_list_files to understand "
        f"what code exists\n"
        f"Step 3: Call project_edit_file to make changes\n\n"
        f"Do NOT reply with text. Call a tool function right now."
    )


def _has_ato_file_changes(traces: list[ToolTrace]) -> bool:
    """Check whether any tool trace represents a successful .ato file modification."""
    for trace in traces:
        if trace.name not in ("project_edit_file", "project_create_path"):
            continue
        if not trace.ok:
            continue
        path = str(trace.args.get("path", ""))
        if path.endswith(".ato"):
            return True
    return False


@dataclass
class _TurnState:
    checklist: Checklist | None = None
    checklist_nudge_count: int = 0
    current_message_id: str = ""
    message_nudge_count: int = 0
    review_items_injected: bool = False
    force_turn_end: bool = False
    consecutive_empty_continuations: int = 0
    silent_retry_count: int = 0
    _traces: list[ToolTrace] = field(default_factory=list)


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


def _resolve_message_id(raw: str | None, fallback: str) -> str | None:
    """Normalize a model-provided message_id.

    If the model made up a value (e.g. ``"user-request"``), fall back to the
    current turn's real message_id.  A valid id is a 32-char hex UUID.
    """
    if not raw or not isinstance(raw, str):
        return fallback or None
    cleaned = raw.strip()
    # Accept 32-char hex strings (uuid4().hex format)
    if len(cleaned) == 32:
        try:
            int(cleaned, 16)
            return cleaned
        except ValueError:
            pass
    # Model made up an id — use the turn's message_id
    return fallback or None


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
        session_id: str = "",
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

        tool_defs = self._registry.definitions()

        breaker = CircuitBreaker()
        traces: list[ToolTrace] = []
        loops = 0
        last_response_id = previous_response_id
        started_at = time.monotonic()
        telemetry: dict[str, Any] = {
            "api_retry_count": 0,
            "compaction_events": [],
            "kickstart_count": 0,
            "silent_retry_count": 0,
            "checklist_tool_count": 0,
            "work_tool_count": 0,
        }

        # Checklist-driven continuation state
        turn_state = _TurnState(
            checklist=Checklist.from_skill_state(skill_state),
            _traces=traces,
        )
        continuations_remaining = cfg.max_checklist_continuations

        # Register this user message in the message log and inject
        # the message_id into the user content so the model can link
        # checklist items to it.
        if session_id:
            now_iso = datetime.now(timezone.utc).isoformat()
            msg_id = uuid.uuid4().hex
            turn_state.current_message_id = msg_id
            try:
                from atopile.model.sqlite import MessageLog

                MessageLog.register_message(
                    TrackedMessage(
                        message_id=msg_id,
                        session_id=session_id,
                        project_root=str(project_path),
                        role="user",
                        content=user_message,
                        status=MSG_PENDING,
                        created_at=now_iso,
                        updated_at=now_iso,
                    )
                )
            except Exception:
                log.warning("Failed to register user message", exc_info=True)

            # Tag the user content with its message_id
            user_content += (
                f"\n\n[message_id={msg_id}] "
                "Use this message_id when creating checklist items "
                "for this request."
            )

        request_input.append({"role": "user", "content": user_content})

        # Consume any early steering
        steering_inputs = self._collect_steering(
            consume_steering_messages,
            session_id=session_id,
            project_root=str(project_path),
        )
        if steering_inputs:
            request_input.extend(steering_inputs)

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
        initial_preamble = _summarize_model_preamble(response.text)
        if initial_preamble and response.tool_calls:
            await self._emit_progress(
                progress_callback,
                {
                    "phase": "thinking",
                    "status_text": "Planning",
                    "detail_text": initial_preamble,
                },
            )
        log.info(
            "Initial response: phase=%s, tool_calls=%d, text_len=%d",
            response.phase,
            len(response.tool_calls),
            len(response.text),
        )

        # ── Main loop ────────────────────────────────────────────────
        while loops < cfg.max_tool_loops:
            elapsed = time.monotonic() - started_at

            loops += 1

            # No tool calls → check phase/checklist/steering, then done
            if not response.tool_calls:
                if elapsed >= cfg.max_turn_seconds:
                    return self._stop(
                        reason="turn_time_budget_exceeded",
                        text=_build_turn_time_budget_stop_text(elapsed, loops, traces),
                        traces=traces,
                        last_response_id=last_response_id,
                        skill_state=skill_state,
                        telemetry=telemetry,
                    )
                # Commentary phase means the model is still working (preamble
                # text before tool calls).  Re-prompt so it can continue.
                if response.phase == "commentary":
                    commentary_preamble = _summarize_model_preamble(response.text)
                    await self._emit_progress(
                        progress_callback,
                        {
                            "phase": "thinking",
                            "status_text": "Working",
                            "detail_text": commentary_preamble
                            or "Continuing after preamble",
                        },
                    )
                    await self._emit_trace(
                        active_trace,
                        "commentary_continuation",
                        {
                            "loop": loops,
                            "text_len": len(response.text),
                            "text_preview": commentary_preamble,
                        },
                    )
                    response = await self._provider.complete(
                        messages=[],
                        instructions=instructions,
                        tools=tool_defs,
                        skill_state=skill_state,
                        project_path=project_path,
                        previous_response_id=last_response_id,
                    )
                    last_response_id = response.id or last_response_id
                    continued_preamble = _summarize_model_preamble(response.text)
                    if continued_preamble and response.tool_calls:
                        await self._emit_progress(
                            progress_callback,
                            {
                                "phase": "thinking",
                                "status_text": "Working",
                                "detail_text": continued_preamble,
                            },
                        )
                    continue

                # Checklist continuation: if there's an active checklist
                # with incomplete items, continue the turn.
                # Guard against the model being stuck: if it responds
                # text-only to several consecutive continuation nudges,
                # stop nudging and let the turn end.
                cl = turn_state.checklist
                _has_incomplete_checklist = (
                    cl is not None
                    and not cl.all_terminal()
                    and continuations_remaining > 0
                )
                if _has_incomplete_checklist:
                    turn_state.consecutive_empty_continuations += 1

                    # Detect if the model produced an empty response,
                    # thinks tools are unavailable, or just isn't acting.
                    resp_text = (response.text or "").strip()
                    resp_lower = resp_text.lower()
                    _is_empty = len(resp_text) == 0
                    _model_thinks_stuck = any(
                        pat in resp_lower for pat in _STUCK_TOOL_PATTERNS
                    )
                    _needs_kickstart = _is_empty or _model_thinks_stuck

                    if (
                        _needs_kickstart
                        and turn_state.consecutive_empty_continuations
                        <= _MAX_EMPTY_CONTINUATIONS
                    ):
                        # Silent retry: re-prompt with empty messages
                        # (same pattern as commentary continuation) before
                        # falling back to a kickstart user-message injection.
                        if turn_state.silent_retry_count < cfg.silent_retry_max:
                            turn_state.silent_retry_count += 1
                            log.info(
                                "Silent retry %d/%d (empty=%s, streak=%d)",
                                turn_state.silent_retry_count,
                                cfg.silent_retry_max,
                                _is_empty,
                                turn_state.consecutive_empty_continuations,
                            )
                            await self._emit_trace(
                                active_trace,
                                "silent_retry",
                                {
                                    "loop": loops,
                                    "attempt": turn_state.silent_retry_count,
                                    "max": cfg.silent_retry_max,
                                    "empty_streak": turn_state.consecutive_empty_continuations,
                                },
                            )
                            telemetry["silent_retry_count"] = (
                                telemetry.get("silent_retry_count", 0) + 1
                            )
                            response = await self._provider.complete(
                                messages=[],
                                instructions=instructions,
                                tools=tool_defs,
                                skill_state=skill_state,
                                project_path=project_path,
                                previous_response_id=last_response_id,
                            )
                            last_response_id = response.id or last_response_id
                            continue

                        # Silent retries exhausted — fall back to kickstart
                        continuations_remaining -= 1
                        kickstart_msg = _build_kickstart_msg(cl)
                        log.warning(
                            "Model stuck (empty=%s, thinks_stuck=%s, streak=%d, "
                            "silent_retries_exhausted=True), sending kickstart",
                            _is_empty,
                            _model_thinks_stuck,
                            turn_state.consecutive_empty_continuations,
                        )
                        await self._emit_trace(
                            active_trace,
                            "tool_kickstart",
                            {
                                "loop": loops,
                                "empty_streak": turn_state.consecutive_empty_continuations,
                                "is_empty": _is_empty,
                                "model_thinks_stuck": _model_thinks_stuck,
                                "model_text_snippet": resp_text[:200],
                                "silent_retries_exhausted": True,
                            },
                        )
                        telemetry["kickstart_count"] = (
                            telemetry.get("kickstart_count", 0) + 1
                        )
                        response = await self._provider.complete(
                            messages=[{"role": "user", "content": kickstart_msg}],
                            instructions=instructions,
                            tools=tool_defs,
                            skill_state=skill_state,
                            project_path=project_path,
                            previous_response_id=last_response_id,
                        )
                        last_response_id = response.id or last_response_id
                        continue
                    elif (
                        turn_state.consecutive_empty_continuations
                        <= _MAX_EMPTY_CONTINUATIONS
                    ):
                        continuations_remaining -= 1
                        cont_msg = cl.continuation_prompt()
                        cl.save_to_skill_state(skill_state)
                        log.info(
                            "Checklist continuation (remaining=%d, loop=%d, "
                            "incomplete=%d, empty_streak=%d)",
                            continuations_remaining,
                            loops,
                            len(cl.incomplete_items()),
                            turn_state.consecutive_empty_continuations,
                        )
                        await self._emit_progress(
                            progress_callback,
                            {
                                "phase": "thinking",
                                "status_text": "Continuing",
                                "detail_text": (
                                    f"{len(cl.incomplete_items())} checklist items remaining"
                                ),
                            },
                        )
                        await self._emit_trace(
                            active_trace,
                            "checklist_continuation",
                            {
                                "loop": loops,
                                "tool_calls_total": len(traces),
                                "continuations_remaining": continuations_remaining,
                                "incomplete_items": len(cl.incomplete_items()),
                                "summary": cl.summary_text(),
                            },
                        )
                        response = await self._provider.complete(
                            messages=[{"role": "user", "content": cont_msg}],
                            instructions=instructions,
                            tools=tool_defs,
                            skill_state=skill_state,
                            project_path=project_path,
                            previous_response_id=last_response_id,
                        )
                        last_response_id = response.id or last_response_id
                        continue
                    else:
                        log.warning(
                            "Model stuck: %d consecutive empty continuations, "
                            "ending turn with incomplete checklist",
                            turn_state.consecutive_empty_continuations,
                        )

                # No checklist yet — nudge the model to create one,
                # but only if it has done real work (read/edit/build/
                # search).  Conversational responses (text-only or
                # trivial tool calls) should not require a checklist.
                has_done_work = telemetry.get("work_tool_count", 0) > 0
                if (
                    has_done_work
                    and turn_state.checklist is None
                    and turn_state.checklist_nudge_count < _MAX_CHECKLIST_NUDGES
                ):
                    turn_state.checklist_nudge_count += 1
                    log.info(
                        "Checklist nudge %d/%d (loop=%d, traces=%d)",
                        turn_state.checklist_nudge_count,
                        _MAX_CHECKLIST_NUDGES,
                        loops,
                        len(traces),
                    )
                    await self._emit_progress(
                        progress_callback,
                        {
                            "phase": "thinking",
                            "status_text": "Continuing",
                            "detail_text": "Requesting checklist creation",
                        },
                    )
                    await self._emit_trace(
                        active_trace,
                        "checklist_nudge",
                        {
                            "loop": loops,
                            "tool_calls_total": len(traces),
                            "nudge_count": turn_state.checklist_nudge_count,
                        },
                    )
                    response = await self._provider.complete(
                        messages=[{"role": "user", "content": _CHECKLIST_NUDGE_MSG}],
                        instructions=instructions,
                        tools=tool_defs,
                        skill_state=skill_state,
                        project_path=project_path,
                        previous_response_id=last_response_id,
                    )
                    last_response_id = response.id or last_response_id
                    continue

                # Pending-message nudge: remind the model about
                # unaddressed messages AFTER it has had a chance to
                # create a checklist organically.  Firing this before
                # the checklist nudge was causing the model to lose the
                # thread of the original task after addressing the
                # meta-task of message acknowledgement.
                if session_id and turn_state.message_nudge_count < _MAX_MESSAGE_NUDGES:
                    try:
                        from atopile.model.sqlite import MessageLog

                        pending = MessageLog.get_pending_messages(session_id)
                    except Exception:
                        pending = []
                    if pending:
                        turn_state.message_nudge_count += 1
                        nudge = build_pending_message_nudge(pending)
                        log.info(
                            "Message nudge %d/%d (loop=%d, pending=%d)",
                            turn_state.message_nudge_count,
                            _MAX_MESSAGE_NUDGES,
                            loops,
                            len(pending),
                        )
                        await self._emit_trace(
                            active_trace,
                            "message_nudge",
                            {
                                "loop": loops,
                                "nudge_count": turn_state.message_nudge_count,
                                "pending_count": len(pending),
                            },
                        )
                        response = await self._provider.complete(
                            messages=[{"role": "user", "content": nudge}],
                            instructions=instructions,
                            tools=tool_defs,
                            skill_state=skill_state,
                            project_path=project_path,
                            previous_response_id=last_response_id,
                        )
                        last_response_id = response.id or last_response_id
                        continue

                steering = self._collect_steering(
                    consume_steering_messages,
                    session_id=session_id,
                    project_root=str(project_path),
                )
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

                # Persist checklist state before returning
                if turn_state.checklist is not None:
                    turn_state.checklist.save_to_skill_state(skill_state)

                text = response.text or "No assistant response produced."
                await self._emit_trace(
                    active_trace,
                    "turn_completed",
                    {
                        "loop": loops,
                        "tool_calls_total": len(traces),
                        "response_id": response.id,
                        "phase": response.phase,
                    },
                )
                done_payload: dict[str, Any] = {
                    "phase": "done",
                    "loop": loops,
                    "tool_calls_total": len(traces),
                }
                if turn_state.checklist is not None:
                    done_payload["checklist"] = turn_state.checklist.to_dict()
                await self._emit_progress(progress_callback, done_payload)
                return AgentTurnResult(
                    text=text,
                    tool_traces=traces,
                    model=cfg.model,
                    response_id=last_response_id,
                    skill_state=skill_state,
                    context_metrics=telemetry,
                )

            # Execute tool calls — decay (not hard-reset) the empty-
            # continuation streak so a persistent pattern still triggers,
            # and reset silent retries for the next potential empty response.
            turn_state.consecutive_empty_continuations = max(
                0, turn_state.consecutive_empty_continuations - 2
            )
            turn_state.silent_retry_count = 0
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

                # Intercept managed tools — handled in-process, not
                # dispatched to the registry.
                if call.name in _MANAGED_TOOLS:
                    args = call.arguments or {}
                    result_payload, ok = self._handle_managed_tool(
                        call.name,
                        args,
                        turn_state,
                        skill_state,
                        session_id=session_id,
                        project_root=str(project_path),
                    )
                    # Emit structured questions to frontend
                    if call.name == "design_questions" and ok:
                        await self._emit_progress(
                            progress_callback,
                            {
                                "phase": "design_questions",
                                "context": (call.arguments or {}).get("context", ""),
                                "questions": (call.arguments or {}).get(
                                    "questions", []
                                ),
                            },
                        )
                else:
                    args, result_payload, ok = await self._execute_tool(
                        tool_name=call.name,
                        raw_args=call.arguments_raw,
                        parsed_args=call.arguments,
                        project_path=project_path,
                        ctx=ctx,
                    )

                trace = ToolTrace(
                    name=call.name, args=args, ok=ok, result=result_payload
                )
                traces.append(trace)

                if ok:
                    breaker.record_success()

                    # Auto-doing: when the model calls a work tool
                    # but hasn't explicitly moved any checklist item
                    # to "doing", auto-transition the first
                    # "not_started" item so the checklist stays in
                    # sync without an extra tool call.
                    if call.name in _WORK_TOOLS:
                        telemetry["work_tool_count"] = (
                            telemetry.get("work_tool_count", 0) + 1
                        )
                        cl = turn_state.checklist
                        if cl is not None and not any(
                            i.status == "doing" for i in cl.items
                        ):
                            for item in cl.items:
                                if item.status == "not_started":
                                    item.status = "doing"
                                    cl.save_to_skill_state(skill_state)
                                    await self._emit_trace(
                                        active_trace,
                                        "checklist_auto_doing",
                                        {"item_id": item.id, "tool": call.name},
                                    )
                                    break
                        elif cl is None and loops > 1:
                            # Model is working without a checklist —
                            # create an implicit one so continuations
                            # and the "incomplete items" logic can work.
                            turn_state.checklist = Checklist(
                                items=[
                                    ChecklistItem(
                                        id="task_1",
                                        description="Complete user request",
                                        criteria="User request fulfilled",
                                        status="doing",
                                    )
                                ],
                                created_at=time.time(),
                            )
                            turn_state.checklist.save_to_skill_state(skill_state)
                            await self._emit_trace(
                                active_trace,
                                "checklist_implicit_created",
                                {"tool": call.name, "loop": loops},
                            )
                    elif call.name in _CHECKLIST_TOOLS:
                        telemetry["checklist_tool_count"] = (
                            telemetry.get("checklist_tool_count", 0) + 1
                        )
                else:
                    trip_msg = breaker.record_failure(
                        call.name, args, str(result_payload.get("error", ""))
                    )
                    if trip_msg:
                        result_payload["circuit_breaker"] = trip_msg
                        await self._emit_trace(
                            active_trace,
                            "circuit_breaker",
                            {"tool": call.name, "message": trip_msg},
                        )

                tool_end_payload: dict[str, Any] = {
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
                }
                # Attach checklist snapshot whenever it changes
                if call.name in _MANAGED_TOOLS and turn_state.checklist:
                    tool_end_payload["checklist"] = turn_state.checklist.to_dict()
                await self._emit_progress(progress_callback, tool_end_payload)
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

            # Force turn end (e.g. after design_questions)
            if turn_state.force_turn_end:
                log.info("Force turn end (loop=%d, traces=%d)", loops, len(traces))
                last_response_id = await self._close_provider_tool_chain(
                    outputs=outputs,
                    instructions=instructions,
                    skill_state=skill_state,
                    project_path=project_path,
                    previous_response_id=last_response_id,
                    active_trace=active_trace,
                    loops=loops,
                    reason="force_turn_end",
                )
                if turn_state.checklist is not None:
                    turn_state.checklist.save_to_skill_state(skill_state)
                await self._emit_trace(
                    active_trace,
                    "turn_completed",
                    {
                        "loop": loops,
                        "tool_calls_total": len(traces),
                        "reason": "design_questions",
                    },
                )
                done_payload: dict[str, Any] = {
                    "phase": "done",
                    "loop": loops,
                    "tool_calls_total": len(traces),
                    "reason": "design_questions",
                }
                if turn_state.checklist is not None:
                    done_payload["checklist"] = turn_state.checklist.to_dict()
                await self._emit_progress(progress_callback, done_payload)
                return AgentTurnResult(
                    text="",
                    tool_traces=traces,
                    model=cfg.model,
                    response_id=last_response_id,
                    skill_state=skill_state,
                    context_metrics=telemetry,
                )

            # Append steering if available
            steering = self._collect_steering(
                consume_steering_messages,
                session_id=session_id,
                project_root=str(project_path),
            )
            if steering:
                outputs.extend(steering)

            elapsed_after_tools = time.monotonic() - started_at
            if elapsed_after_tools >= cfg.max_turn_seconds:
                last_response_id = await self._close_provider_tool_chain(
                    outputs=outputs,
                    instructions=instructions,
                    skill_state=skill_state,
                    project_path=project_path,
                    previous_response_id=last_response_id,
                    active_trace=active_trace,
                    loops=loops,
                    reason="turn_time_budget_exceeded",
                )
                return self._stop(
                    reason="turn_time_budget_exceeded",
                    text=_build_turn_time_budget_stop_text(
                        elapsed_after_tools, loops, traces
                    ),
                    traces=traces,
                    last_response_id=last_response_id,
                    skill_state=skill_state,
                    telemetry=telemetry,
                )

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

    async def _close_provider_tool_chain(
        self,
        *,
        outputs: list[dict[str, Any]],
        instructions: str,
        skill_state: dict[str, Any],
        project_path: Path,
        previous_response_id: str | None,
        active_trace: TraceCallback | None,
        loops: int,
        reason: str,
    ) -> str | None:
        if not outputs:
            return previous_response_id

        closing_response = await self._provider.complete(
            messages=outputs,
            instructions=instructions,
            tools=[],
            skill_state=skill_state,
            project_path=project_path,
            previous_response_id=previous_response_id,
        )
        next_response_id = closing_response.id or previous_response_id
        if closing_response.tool_calls:
            await self._emit_trace(
                active_trace,
                "provider_chain_closed_with_ignored_tool_calls",
                {
                    "loop": loops,
                    "reason": reason,
                    "tool_calls_total": len(closing_response.tool_calls),
                    "tool_names": [call.name for call in closing_response.tool_calls],
                },
            )
        return next_response_id

    @staticmethod
    def _handle_managed_tool(
        tool_name: str,
        args: dict[str, Any],
        state: _TurnState,
        skill_state: dict[str, Any],
        *,
        session_id: str = "",
        project_root: str = "",
    ) -> tuple[dict[str, Any], bool]:
        """Handle checklist + message + planning tools in-process."""
        try:
            # ── Planning tools ─────────────────────────────────────
            if tool_name == "design_questions":
                context = str(args.get("context", ""))
                questions = args.get("questions", [])
                if not questions:
                    return {"error": "questions list is empty"}, False
                if state.checklist is not None:
                    for item in state.checklist.items:
                        if item.id == "questions" and item.status in {
                            "not_started",
                            "doing",
                        }:
                            item.status = "done"
                            break
                    state.checklist.save_to_skill_state(skill_state)
                # Signal the runner to end the turn after this tool call.
                state.force_turn_end = True
                return {
                    "ok": True,
                    "status": "questions_sent",
                    "question_count": len(questions),
                    "message": (
                        "Design questions sent to the user. "
                        "Your turn is ending now — the user's answers "
                        "will arrive as a new message."
                    ),
                }, True

            # ── Message tools ──────────────────────────────────────
            if tool_name == "message_acknowledge":
                message_id = str(args.get("message_id", ""))
                justification = str(args.get("justification", "")).strip()
                if not message_id or not justification:
                    return {"error": "message_id and justification are required"}, False
                if len(justification.split()) < 3:
                    return {
                        "error": (
                            "Justification must be a meaningful sentence "
                            "(at least a few words explaining why no action is needed)."
                        )
                    }, False
                try:
                    from atopile.model.sqlite import MessageLog

                    msg = MessageLog.get_message(message_id)
                    if msg is None:
                        return {"error": f"Message '{message_id}' not found."}, False
                    if msg.status != MSG_PENDING:
                        return {
                            "error": (
                                f"Message '{message_id}' has status "
                                f"'{msg.status}', expected 'pending'."
                            )
                        }, False
                    MessageLog.update_message_status(
                        message_id, MSG_ACKNOWLEDGED, justification
                    )
                except ImportError:
                    return {"error": "MessageLog not available"}, False
                return {
                    "ok": True,
                    "message_id": message_id,
                    "status": MSG_ACKNOWLEDGED,
                }, True

            if tool_name == "message_log_query":
                scope = str(args.get("scope", "thread"))
                q_status = args.get("status")
                q_search = args.get("search")
                include_items = bool(args.get("include_items", False))
                q_limit = int(args.get("limit", 20))
                try:
                    from atopile.model.sqlite import MessageLog

                    query_kwargs: dict[str, Any] = {
                        "status": q_status,
                        "search": q_search,
                        "include_items": include_items,
                        "limit": q_limit,
                    }
                    if scope == "project":
                        query_kwargs["project_root"] = project_root
                    else:
                        query_kwargs["session_id"] = session_id
                    result = MessageLog.query(**query_kwargs)
                except ImportError:
                    result = {"messages": [], "total": 0}
                return result, True

            # ── Checklist tools ──────────────────────────────────
            if tool_name == "checklist_create":
                raw_items = args.get("items", [])
                if not raw_items:
                    return {"error": "items list is empty"}, False
                if state.checklist is not None:
                    return {
                        "error": "Checklist already exists. Use checklist_update."
                    }, False

                now_iso = datetime.now(timezone.utc).isoformat()
                items = [
                    ChecklistItem(
                        id=str(it["id"]),
                        description=str(it["description"]),
                        criteria=str(it["criteria"]),
                        requirement_id=it.get("requirement_id"),
                        source=it.get("source"),
                        message_id=_resolve_message_id(
                            it.get("message_id"), state.current_message_id
                        ),
                    )
                    for it in raw_items
                ]
                state.checklist = Checklist(items=items, created_at=time.time())
                state.checklist.save_to_skill_state(skill_state)

                # Persist items and update linked messages
                if session_id:
                    try:
                        from atopile.model.sqlite import MessageLog

                        linked_message_ids: set[str] = set()
                        for item in items:
                            MessageLog.save_checklist_item(
                                TrackedChecklistItem(
                                    item_id=item.id,
                                    session_id=session_id,
                                    message_id=item.message_id,
                                    description=item.description,
                                    criteria=item.criteria,
                                    status=item.status,
                                    requirement_id=item.requirement_id,
                                    source=item.source,
                                    created_at=now_iso,
                                    updated_at=now_iso,
                                )
                            )
                            if item.message_id:
                                linked_message_ids.add(item.message_id)
                        for mid in linked_message_ids:
                            msg = MessageLog.get_message(mid)
                            if msg and msg.status == MSG_PENDING:
                                MessageLog.update_message_status(mid, MSG_ACTIVE)
                    except Exception:
                        log.warning("Failed to persist checklist items", exc_info=True)

                return {
                    "ok": True,
                    "message": f"Checklist created with {len(items)} items.",
                    "checklist": state.checklist.summary_text(),
                }, True

            elif tool_name == "checklist_add_items":
                if state.checklist is None:
                    return {
                        "error": "No checklist exists. Call checklist_create first."
                    }, False
                raw_items = args.get("items", [])
                if not raw_items:
                    return {"error": "items list is empty"}, False

                now_iso = datetime.now(timezone.utc).isoformat()
                existing_ids = {i.id for i in state.checklist.items}
                skipped: list[str] = []
                added: list[ChecklistItem] = []
                for it in raw_items:
                    item_id = str(it["id"])
                    if item_id in existing_ids:
                        skipped.append(item_id)
                        continue
                    item = ChecklistItem(
                        id=item_id,
                        description=str(it["description"]),
                        criteria=str(it["criteria"]),
                        requirement_id=it.get("requirement_id"),
                        source=it.get("source"),
                        message_id=_resolve_message_id(
                            it.get("message_id"), state.current_message_id
                        ),
                    )
                    added.append(item)
                    existing_ids.add(item_id)
                state.checklist.items.extend(added)
                state.checklist.save_to_skill_state(skill_state)

                # Persist items and update linked messages
                if session_id:
                    try:
                        from atopile.model.sqlite import MessageLog

                        linked_message_ids: set[str] = set()
                        for item in added:
                            MessageLog.save_checklist_item(
                                TrackedChecklistItem(
                                    item_id=item.id,
                                    session_id=session_id,
                                    message_id=item.message_id,
                                    description=item.description,
                                    criteria=item.criteria,
                                    status=item.status,
                                    requirement_id=item.requirement_id,
                                    source=item.source,
                                    created_at=now_iso,
                                    updated_at=now_iso,
                                )
                            )
                            if item.message_id:
                                linked_message_ids.add(item.message_id)
                        for mid in linked_message_ids:
                            msg = MessageLog.get_message(mid)
                            if msg and msg.status == MSG_PENDING:
                                MessageLog.update_message_status(mid, MSG_ACTIVE)
                    except Exception:
                        log.warning(
                            "Failed to persist added checklist items", exc_info=True
                        )

                msg = f"Added {len(added)} item(s)."
                if skipped:
                    msg += (
                        f" Skipped {len(skipped)} duplicate(s): {', '.join(skipped)}."
                    )
                return {
                    "ok": True,
                    "message": msg,
                    "added": len(added),
                    "skipped": skipped,
                    "checklist": state.checklist.summary_text(),
                }, True

            elif tool_name == "checklist_update":
                if state.checklist is None:
                    return {
                        "error": "No checklist exists. Call checklist_create first."
                    }, False
                item_id = str(args.get("item_id", ""))
                new_status = str(args.get("status", ""))
                justification = args.get("justification")
                target = next(
                    (i for i in state.checklist.items if i.id == item_id), None
                )
                if target is None:
                    return {"error": f"Item '{item_id}' not found."}, False
                # Treat same-status transitions as a harmless no-op.
                # This avoids errors when auto-doing already moved an
                # item to "doing" before the model explicitly requests it.
                if target.status == new_status:
                    return {
                        "ok": True,
                        "item_id": item_id,
                        "status": new_status,
                        "noop": True,
                        "checklist": state.checklist.summary_text(),
                    }, True
                allowed = VALID_TRANSITIONS.get(target.status, set())
                if new_status not in allowed:
                    return {
                        "error": (
                            f"Cannot transition '{item_id}' from "
                            f"'{target.status}' to '{new_status}'. "
                            f"Allowed: {sorted(allowed) or 'none (terminal)'}."
                        )
                    }, False
                target.status = new_status
                if justification:
                    target.justification = str(justification)
                state.checklist.save_to_skill_state(skill_state)

                # Persist status change and check for message completion
                if session_id:
                    try:
                        from atopile.model.sqlite import MessageLog

                        MessageLog.update_checklist_item(
                            session_id,
                            item_id,
                            new_status,
                            str(justification) if justification else None,
                        )
                        MessageLog.check_and_complete_messages(session_id)
                    except Exception:
                        log.warning("Failed to persist checklist update", exc_info=True)

                # Auto-inject design review items when the last
                # user-created item becomes terminal and .ato files
                # were modified.  This keeps the agent working through
                # review before the turn ends.
                result: dict[str, Any] = {
                    "ok": True,
                    "item_id": item_id,
                    "status": new_status,
                    "checklist": state.checklist.summary_text(),
                }
                if (
                    not state.review_items_injected
                    and new_status in ("done", "blocked")
                    and all(
                        i.status in ("done", "blocked")
                        for i in state.checklist.items
                        if i.source != "review"
                    )
                    and _has_ato_file_changes(state._traces)
                ):
                    state.review_items_injected = True
                    for ri in _DESIGN_REVIEW_ITEMS:
                        state.checklist.items.append(copy.deepcopy(ri))
                    state.checklist.save_to_skill_state(skill_state)
                    result["review_items_added"] = True
                    result["checklist"] = state.checklist.summary_text()
                    result["message"] = (
                        "Review items added to your checklist. "
                        "Work through each review item before finishing."
                    )

                return result, True

            return {"error": f"Unknown managed tool: {tool_name}"}, False
        except Exception as exc:
            return {"error": str(exc), "error_type": type(exc).__name__}, False

    @staticmethod
    def _collect_steering(
        consume_steering_messages: SteeringMessagesCallback | None,
        session_id: str = "",
        project_root: str = "",
    ) -> list[dict[str, Any]]:
        messages = _consume_steering_updates(consume_steering_messages)
        if not messages:
            return []

        # Register steering messages in the message log
        message_ids: list[str] = []
        if session_id:
            now_iso = datetime.now(timezone.utc).isoformat()
            try:
                from atopile.model.sqlite import MessageLog

                for msg_text in messages:
                    mid = uuid.uuid4().hex
                    MessageLog.register_message(
                        TrackedMessage(
                            message_id=mid,
                            session_id=session_id,
                            project_root=project_root,
                            role="steering",
                            content=msg_text,
                            status=MSG_PENDING,
                            created_at=now_iso,
                            updated_at=now_iso,
                        )
                    )
                    message_ids.append(mid)
            except Exception:
                log.warning("Failed to register steering messages", exc_info=True)

        return _build_steering_inputs_for_model(messages, message_ids=message_ids)

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
