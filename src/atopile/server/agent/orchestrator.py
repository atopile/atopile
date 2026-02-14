"""Server-side agent orchestration with strict tool execution."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from atopile.dataclasses import AppContext
from atopile.model import builds as builds_domain
from atopile.server.agent import policy, tools
from atopile.server.agent import skills as skills_domain
from atopile.server.domains import artifacts as artifacts_domain

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]
MessageCallback = Callable[[dict[str, Any]], Awaitable[None] | None]
SteeringMessagesCallback = Callable[[], list[str]]
_RETRY_AFTER_TEXT_PATTERN = re.compile(
    r"Please try again in\s*(\d+(?:\.\d+)?)\s*(ms|s)\b",
    re.IGNORECASE,
)

_SYSTEM_PROMPT = """You are the atopile agent inside the sidebar.

Rules:
- Use tools for project inspection, edits, installs, builds, logs, and
  BOM/variables/manufacturing checks.
- Do not suggest shell commands to the user.
- Keep responses concise and implementation-focused.
- Always respect the selected project scope.
- Before editing files, inspect relevant files first with project_read_file.
- For edits, use project_edit_file with LINE:HASH anchors copied exactly from
  project_read_file output.
- Batch known edits for one file in a single project_edit_file call.
- If project_edit_file returns hash mismatch remaps, retry with remapped
  anchors before re-reading unless more context is needed.
- Use project_rename_path and project_delete_path for scoped file operations
  when requested.
- Avoid project_write_file and project_replace_text unless explicitly asked for
  compatibility.
- Use parts_search/parts_install for physical LCSC/JLC components and
  packages_search/packages_install for atopile registry dependencies.
- Use stdlib_list and stdlib_get_item when selecting/understanding standard
  library modules, interfaces, and traits.
- Use examples_list/examples_search/examples_read_ato for curated reference
  `.ato` examples when authoring or explaining DSL patterns.
- Use datasheet_read when a component datasheet is needed; it attaches a PDF
  file for native model reading. Prefer lcsc_id to resolve via project graph.
- Use project_list_modules and project_module_children for quick structure
  discovery before deep file reads.
- Package source files live under `.ato/modules/...` (legacy `.ato/deps/...`
  paths may appear; prefer `.ato/modules`).
- If asked for design structure/architecture, call project_list_modules before
  answering and use project_module_children for any key entry points.
- If asked for BOM/parts list/procurement summary, call report_bom first (do
  not infer BOM from source files).
- If asked for parameters/constraints/computed values, call report_variables
  first (do not infer parameter values from source files).
- If asked to generate manufacturing outputs, call manufacturing_generate
  first, then track with build_logs_search, then inspect with
  manufacturing_summary.
- For PCB placement/routing automation, use autolayout_run (background), then
  autolayout_status to monitor candidates, then autolayout_fetch_to_layout to
  apply/archive selected results under layouts/.
- If asked to control ground pours/planes/stackup assumptions, call
  autolayout_configure_board_intent before running placement/routing.
- Use periodic check-ins for active autolayout jobs (autolayout_status with
  wait_seconds/poll_interval_seconds). If quality is not good enough, resume by
  calling autolayout_run with resume_board_id and additional timeout.
- Time-budget heuristic: simple boards (<=50 components) start around 2-4 min,
  medium (50-100) around 10-15 min, larger boards often 20+ min with iterative
  resume runs.
- For board preview images after placement/routing, use
  autolayout_request_screenshot and track the queued build with build_logs_search.
- For build diagnostics, prefer build_logs_search with explicit log_levels/stage
  filters when logs are noisy.
- Use design_diagnostics when a build fails silently or diagnostics are needed.
- For significant multi-step tasks, use a short markdown checklist in your reply
  and mark completed items as you progress.
- End with a concise completion summary of what was done.
- Suggest one concrete next step and ask whether to continue.
- After editing, explain exactly which files changed.
"""

_MANAGER_PLANNER_PROMPT = """You are the conversation manager for atopile.

Your job:
- Track and preserve user intent exactly.
- Convert user request into a crisp worker brief.
- Define acceptance criteria.
- Keep scope and constraints explicit.

Return JSON only with this shape:
{
  "intent_summary": string,
  "objective": string,
  "constraints": [string, ...],
  "acceptance_criteria": [string, ...],
  "worker_brief": string,
  "checkpoints": [string, ...]
}

Rules:
- Keep worker_brief concrete and implementation-focused.
- Do not include markdown in JSON fields.
- If uncertain, encode uncertainty as constraints/checkpoints rather than asking
  for a user clarification immediately.
"""

_MANAGER_REVIEW_PROMPT = """You are the conversation manager for atopile.

Review the worker's output and decide whether to accept or refine.

Return JSON only with this shape:
{
  "decision": "accept" | "refine",
  "refinement_brief": string,
  "final_response": string,
  "completion_summary": string
}

Rules:
- Use "accept" when acceptance criteria are satisfied.
- Use "refine" only when there is a concrete, actionable gap.
- Keep refinement_brief implementation-focused.
- final_response must be suitable to show the user directly.
"""


def _build_session_primer(
    *,
    project_root: Path,
    selected_targets: list[str],
) -> str:
    targets = selected_targets if selected_targets else ["<none>"]
    targets_text = ", ".join(targets)
    return (
        "Session primer (one-time orientation):\n"
        f"- project_root: {project_root}\n"
        f"- selected_targets: {targets_text}\n"
        "- workflow: inspect with project_list_modules/project_read_file, then edit\n"
        "  with project_edit_file anchors (LINE:HASH), then verify with build tools.\n"
        "- components: use parts_search/parts_install for physical parts and\n"
        "  packages_search/packages_install for atopile package deps.\n"
        "- diagnostics: on build failures, prefer build_logs_search (INFO first)\n"
        "  and design_diagnostics before broad retries.\n"
        "- stdlib: use stdlib_list and stdlib_get_item for module/interface lookup.\n"
        "- examples: use examples_list/examples_search/examples_read_ato for\n"
        "  curated reference `.ato` code patterns.\n"
        "- reports: for BOM/parts lists use report_bom; for computed parameters\n"
        "  and constraints use report_variables.\n"
        "- manufacturing: use manufacturing_generate to create artifacts, then\n"
        "  build_logs_search to track, then manufacturing_summary to inspect.\n"
        "- pcb auto layout: use autolayout_run for placement/routing, then\n"
        "  autolayout_status to monitor, then autolayout_fetch_to_layout to\n"
        "  apply + archive board iterations.\n"
        "- planes/stackup: use autolayout_configure_board_intent to encode\n"
        "  ground pour and stackup assumptions in ato.yaml before routing.\n"
        "- time-budget heuristic: <=50 components ~2-4 minutes, 50-100 ~10-15\n"
        "  minutes, larger boards 20+ minutes. Resume incrementally if needed.\n"
        "- quality loop: check in periodically with autolayout_status\n"
        "  (wait_seconds/poll_interval_seconds), and if quality is insufficient,\n"
        "  call autolayout_run with resume_board_id for extra time.\n"
        "- screenshots: use autolayout_request_screenshot (2d/3d), then\n"
        "  build_logs_search to track completion and read output paths.\n"
        "- datasheets: use datasheet_read to attach component PDFs for native\n"
        "  model reading (instead of scraping text manually). Prefer lcsc_id\n"
        "  for graph-first resolution."
    )


@dataclass
class ToolTrace:
    name: str
    args: dict[str, Any]
    ok: bool
    result: dict[str, Any]


@dataclass
class AgentPeerMessage:
    message_id: str
    thread_id: str
    from_agent: str
    to_agent: str
    kind: str
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)
    visibility: str = "internal"
    priority: str = "normal"
    requires_ack: bool = False
    correlation_id: str | None = None
    parent_id: str | None = None
    created_at: float = field(default_factory=time.time)


@dataclass
class AgentTurnResult:
    text: str
    tool_traces: list[ToolTrace]
    model: str
    response_id: str | None = None
    skill_state: dict[str, Any] = field(default_factory=dict)
    context_metrics: dict[str, Any] = field(default_factory=dict)
    agent_messages: list[dict[str, Any]] = field(default_factory=list)


class AgentOrchestrator:
    def __init__(self) -> None:
        self.base_url = os.getenv("ATOPILE_AGENT_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("ATOPILE_AGENT_MODEL", "gpt-5-codex")
        self.api_key = os.getenv("ATOPILE_AGENT_OPENAI_API_KEY") or os.getenv(
            "OPENAI_API_KEY"
        )
        self.timeout_s = float(os.getenv("ATOPILE_AGENT_TIMEOUT_S", "120"))
        self.max_tool_loops = int(os.getenv("ATOPILE_AGENT_MAX_TOOL_LOOPS", "1000"))
        self.api_retries = int(os.getenv("ATOPILE_AGENT_API_RETRIES", "4"))
        self.api_retry_base_delay_s = float(
            os.getenv("ATOPILE_AGENT_API_RETRY_BASE_DELAY_S", "0.5")
        )
        self.api_retry_max_delay_s = float(
            os.getenv("ATOPILE_AGENT_API_RETRY_MAX_DELAY_S", "8.0")
        )
        self.skills_dir = Path(
            os.getenv(
                "ATOPILE_AGENT_SKILLS_DIR",
                "/Users/narayanpowderly/projects/atopile/.claude/skills",
            )
        ).expanduser()
        self.skill_top_k = int(os.getenv("ATOPILE_AGENT_SKILL_TOP_K", "3"))
        self.skill_card_max_chars = int(
            os.getenv("ATOPILE_AGENT_SKILL_CARD_MAX_CHARS", "1800")
        )
        self.skill_total_max_chars = int(
            os.getenv("ATOPILE_AGENT_SKILL_TOTAL_MAX_CHARS", "6000")
        )
        self.skill_index_ttl_s = float(
            os.getenv("ATOPILE_AGENT_SKILL_INDEX_TTL_S", "10")
        )
        self.prefix_max_chars = int(
            os.getenv("ATOPILE_AGENT_PREFIX_MAX_CHARS", "18000")
        )
        self.context_summary_max_chars = int(
            os.getenv("ATOPILE_AGENT_CONTEXT_SUMMARY_MAX_CHARS", "8000")
        )
        self.user_message_max_chars = int(
            os.getenv("ATOPILE_AGENT_USER_MESSAGE_MAX_CHARS", "12000")
        )
        self.tool_output_max_chars = int(
            os.getenv("ATOPILE_AGENT_TOOL_OUTPUT_MAX_CHARS", "10000")
        )
        self.context_compact_threshold = int(
            os.getenv("ATOPILE_AGENT_CONTEXT_COMPACT_THRESHOLD", "120000")
        )
        self.context_hard_max_tokens = int(
            os.getenv("ATOPILE_AGENT_CONTEXT_HARD_MAX_TOKENS", "170000")
        )
        self.prompt_cache_retention = os.getenv(
            "ATOPILE_AGENT_PROMPT_CACHE_RETENTION", "24h"
        )
        self.manager_model = os.getenv("ATOPILE_AGENT_MANAGER_MODEL", self.model)
        self.enable_duo_agents = os.getenv(
            "ATOPILE_AGENT_ENABLE_DUO", "1"
        ).strip().lower() not in {"0", "false", "no"}
        self.manager_refine_rounds = int(
            os.getenv("ATOPILE_AGENT_MANAGER_REFINE_ROUNDS", "1")
        )
        self.manager_refine_rounds = max(0, min(self.manager_refine_rounds, 3))
        self._client: AsyncOpenAI | None = None

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
    ) -> AgentTurnResult:
        if self.enable_duo_agents:
            return await self._run_duo_turn(
                ctx=ctx,
                project_root=project_root,
                history=history,
                user_message=user_message,
                selected_targets=selected_targets,
                previous_response_id=previous_response_id,
                tool_memory=tool_memory,
                progress_callback=progress_callback,
                consume_steering_messages=consume_steering_messages,
                message_callback=message_callback,
            )
        return await self._run_worker_turn(
            ctx=ctx,
            project_root=project_root,
            history=history,
            user_message=user_message,
            selected_targets=selected_targets,
            previous_response_id=previous_response_id,
            tool_memory=tool_memory,
            progress_callback=progress_callback,
            consume_steering_messages=consume_steering_messages,
        )

    async def _run_worker_turn(
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
        actor: str = "worker",
    ) -> AgentTurnResult:
        if not self.api_key:
            raise RuntimeError(
                "Missing API key. Set ATOPILE_AGENT_OPENAI_API_KEY or OPENAI_API_KEY."
            )

        project_path = tools.validate_tool_scope(project_root, ctx)
        include_session_primer = previous_response_id is None and len(history) == 0
        context_text = await self._build_context(
            project_root=project_path,
            selected_targets=selected_targets or [],
        )
        context_text = _truncate_middle(
            context_text,
            self.context_summary_max_chars,
        )
        trimmed_user_message = _trim_user_message(
            user_message,
            self.user_message_max_chars,
        )

        skill_selection = skills_domain.select_skills_for_turn(
            skills_dir=self.skills_dir,
            user_message=trimmed_user_message,
            selected_targets=selected_targets or [],
            history=history,
            tool_memory=tool_memory or {},
            top_k=self.skill_top_k,
            per_card_max_chars=self.skill_card_max_chars,
            total_max_chars=self.skill_total_max_chars,
            ttl_s=self.skill_index_ttl_s,
        )
        skill_state = skills_domain.build_skill_state(skill_selection)
        skill_block = skills_domain.render_active_skills_block(skill_selection)

        instructions = _build_turn_instructions(
            include_session_primer=include_session_primer,
            project_root=project_path,
            selected_targets=selected_targets or [],
            skill_block=skill_block,
            max_chars=self.prefix_max_chars,
        )

        history_for_model = history if previous_response_id is None else []

        request_input: list[dict[str, Any]] = list(history_for_model)
        request_input.append(
            {
                "role": "user",
                "content": (
                    f"Project root: {project_path}\n"
                    f"Selected targets: {selected_targets or []}\n"
                    f"Context:\n{context_text}\n\n"
                    f"Request:\n{trimmed_user_message}"
                ),
            }
        )
        request_input.extend(
            _build_steering_inputs_for_model(
                _consume_steering_updates(consume_steering_messages)
            )
        )

        tool_defs = tools.get_tool_definitions_for_actor(actor)
        request_payload: dict[str, Any] = {
            "model": self.model,
            "input": request_input,
            "instructions": instructions,
            "tools": tool_defs,
            "tool_choice": "auto",
            "context_management": [
                {
                    "type": "compaction",
                    "compact_threshold": self.context_compact_threshold,
                }
            ],
            "truncation": "disabled",
            "prompt_cache_key": _build_prompt_cache_key(
                project_path=project_path,
                tool_defs=tool_defs,
                skill_state=skill_state,
                model=self.model,
            ),
            "prompt_cache_retention": self.prompt_cache_retention,
        }
        if previous_response_id:
            request_payload["previous_response_id"] = previous_response_id

        telemetry: dict[str, Any] = {
            "api_retry_count": 0,
            "compaction_events": [],
            "preflight_input_tokens": None,
        }

        await _emit_progress(
            progress_callback,
            {
                "phase": "thinking",
                "status_text": "Planning",
                "detail_text": "Reviewing request and project context",
            },
        )
        response = await self._responses_create_with_context_control(
            payload=request_payload,
            telemetry=telemetry,
            progress_callback=progress_callback,
        )

        traces: list[ToolTrace] = []
        loops = 0
        last_response_id: str | None = response.get("id")
        while loops < self.max_tool_loops:
            loops += 1
            function_calls = _extract_function_calls(response)
            if not function_calls:
                steering_inputs = _build_steering_inputs_for_model(
                    _consume_steering_updates(consume_steering_messages)
                )
                if steering_inputs:
                    await _emit_progress(
                        progress_callback,
                        {
                            "phase": "thinking",
                            "status_text": "Steering",
                            "detail_text": "Applying latest user guidance",
                        },
                    )
                    response = await self._responses_create_with_context_control(
                        payload={
                            "model": self.model,
                            "previous_response_id": response.get("id"),
                            "input": steering_inputs,
                            "instructions": instructions,
                            "tools": tool_defs,
                            "tool_choice": "auto",
                            "context_management": [
                                {
                                    "type": "compaction",
                                    "compact_threshold": self.context_compact_threshold,
                                }
                            ],
                            "truncation": "disabled",
                            "prompt_cache_key": _build_prompt_cache_key(
                                project_path=project_path,
                                tool_defs=tool_defs,
                                skill_state=skill_state,
                                model=self.model,
                            ),
                            "prompt_cache_retention": self.prompt_cache_retention,
                        },
                        telemetry=telemetry,
                        progress_callback=progress_callback,
                        enable_preflight=False,
                    )
                    last_response_id = response.get("id") or last_response_id
                    continue
                text = _extract_text(response)
                if not text:
                    text = "No assistant response produced."
                await _emit_progress(
                    progress_callback,
                    {
                        "phase": "thinking",
                        "status_text": "Composing response",
                    },
                )
                await _emit_progress(
                    progress_callback,
                    {
                        "phase": "done",
                        "loop": loops,
                        "tool_calls_total": len(traces),
                    },
                )
                return AgentTurnResult(
                    text=text,
                    tool_traces=traces,
                    model=self.model,
                    response_id=last_response_id,
                    skill_state=skill_state,
                    context_metrics=telemetry,
                )

            outputs: list[dict[str, Any]] = []
            tool_count = len(function_calls)
            for tool_index, call in enumerate(function_calls, start=1):
                call_id = call.get("call_id") or call.get("id")
                if not call_id:
                    continue

                tool_name = str(call.get("name", ""))
                raw_args = str(call.get("arguments", ""))
                args: dict[str, Any]
                result_payload: dict[str, Any]
                ok = True

                parsed_args: dict[str, Any] | None = None
                try:
                    parsed_args = tools.parse_tool_arguments(raw_args)
                except Exception:
                    parsed_args = None

                await _emit_progress(
                    progress_callback,
                    {
                        "phase": "tool_start",
                        "loop": loops,
                        "tool_index": tool_index,
                        "tool_count": tool_count,
                        "call_id": str(call_id),
                        "name": tool_name,
                        "args": parsed_args if parsed_args is not None else {},
                    },
                )

                try:
                    args = parsed_args if parsed_args is not None else {}
                    if parsed_args is None:
                        args = tools.parse_tool_arguments(raw_args)
                    result_payload = await tools.execute_tool(
                        name=tool_name,
                        arguments=args,
                        project_root=project_path,
                        ctx=ctx,
                        actor=actor,
                    )
                except Exception as exc:
                    args = parsed_args if parsed_args is not None else {}
                    ok = False
                    result_payload = {
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    }
                    remaps = getattr(exc, "remaps", None)
                    if isinstance(remaps, dict):
                        result_payload["remaps"] = remaps
                    mismatches = getattr(exc, "mismatches", None)
                    if isinstance(mismatches, list):
                        result_payload["mismatches"] = [
                            {
                                "line": getattr(mismatch, "line", None),
                                "expected": getattr(mismatch, "expected", None),
                                "actual": getattr(mismatch, "actual", None),
                            }
                            for mismatch in mismatches
                        ]

                traces.append(
                    ToolTrace(
                        name=tool_name,
                        args=args,
                        ok=ok,
                        result=result_payload,
                    )
                )
                await _emit_progress(
                    progress_callback,
                    {
                        "phase": "tool_end",
                        "loop": loops,
                        "tool_index": tool_index,
                        "tool_count": tool_count,
                        "call_id": str(call_id),
                        "trace": {
                            "name": tool_name,
                            "args": args,
                            "ok": ok,
                            "result": result_payload,
                        },
                    },
                )
                outputs.extend(
                    _build_function_call_outputs_for_model(
                        call_id=str(call_id),
                        tool_name=tool_name,
                        result_payload=_limit_tool_output_for_model(
                            _sanitize_tool_output_for_model(result_payload),
                            max_chars=self.tool_output_max_chars,
                        ),
                    )
                )

            steering_inputs = _build_steering_inputs_for_model(
                _consume_steering_updates(consume_steering_messages)
            )
            if steering_inputs:
                outputs.extend(steering_inputs)
                await _emit_progress(
                    progress_callback,
                    {
                        "phase": "thinking",
                        "status_text": "Steering",
                        "detail_text": "Applying latest user guidance",
                        "loop": loops,
                        "tool_calls_total": len(traces),
                    },
                )
            else:
                await _emit_progress(
                    progress_callback,
                    {
                        "phase": "thinking",
                        "status_text": "Reviewing tool results",
                        "detail_text": "Choosing next step",
                        "loop": loops,
                        "tool_calls_total": len(traces),
                    },
                )
            response = await self._responses_create_with_context_control(
                payload={
                    "model": self.model,
                    "previous_response_id": response.get("id"),
                    "input": outputs,
                    "instructions": instructions,
                    "tools": tool_defs,
                    "tool_choice": "auto",
                    "context_management": [
                        {
                            "type": "compaction",
                            "compact_threshold": self.context_compact_threshold,
                        }
                    ],
                    "truncation": "disabled",
                    "prompt_cache_key": _build_prompt_cache_key(
                        project_path=project_path,
                        tool_defs=tool_defs,
                        skill_state=skill_state,
                        model=self.model,
                    ),
                    "prompt_cache_retention": self.prompt_cache_retention,
                },
                telemetry=telemetry,
                progress_callback=progress_callback,
                enable_preflight=False,
            )
            last_response_id = response.get("id") or last_response_id

        await _emit_progress(
            progress_callback,
            {
                "phase": "stopped",
                "reason": "too_many_tool_iterations",
                "loop": loops,
                "tool_calls_total": len(traces),
            },
        )
        return AgentTurnResult(
            text="Stopped after too many tool iterations.",
            tool_traces=traces,
            model=self.model,
            response_id=last_response_id,
            skill_state=skill_state,
            context_metrics=telemetry,
        )

    async def _run_duo_turn(
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
    ) -> AgentTurnResult:
        selected_targets = selected_targets or []
        project_path = tools.validate_tool_scope(project_root, ctx)
        intent_snapshot = await self._manager_build_plan(
            project_path=project_path,
            selected_targets=selected_targets,
            user_message=user_message,
            history=history,
            progress_callback=progress_callback,
        )

        thread_id = f"agent-thread-{uuid.uuid4().hex[:10]}"
        emitted_messages: list[dict[str, Any]] = []

        async def emit_message(
            *,
            from_agent: str,
            to_agent: str,
            kind: str,
            summary: str,
            payload: dict[str, Any] | None = None,
            visibility: str = "internal",
            priority: str = "normal",
            requires_ack: bool = False,
            correlation_id: str | None = None,
            parent_id: str | None = None,
        ) -> dict[str, Any]:
            message = self._new_peer_message(
                thread_id=thread_id,
                from_agent=from_agent,
                to_agent=to_agent,
                kind=kind,
                summary=summary,
                payload=payload or {},
                visibility=visibility,
                priority=priority,
                requires_ack=requires_ack,
                correlation_id=correlation_id,
                parent_id=parent_id,
            )
            data = asdict(message)
            emitted_messages.append(data)
            maybe_awaitable = (
                message_callback(data) if message_callback is not None else None
            )
            if inspect.isawaitable(maybe_awaitable):
                await maybe_awaitable
            return data

        intent_message = await emit_message(
            from_agent="manager",
            to_agent="worker",
            kind="intent_brief",
            summary=intent_snapshot.get("intent_summary", "Prepared worker brief."),
            payload=intent_snapshot,
            visibility="internal",
            requires_ack=True,
        )

        await emit_message(
            from_agent="worker",
            to_agent="manager",
            kind="ack",
            summary="Worker accepted intent brief.",
            payload={"message_id": intent_message["message_id"]},
            visibility="internal",
            parent_id=intent_message["message_id"],
        )

        all_traces: list[ToolTrace] = []
        context_metrics: dict[str, Any] = {"intent_snapshot": intent_snapshot}
        worker_response_id: str | None = previous_response_id
        worker_skill_state: dict[str, Any] = {}
        worker_latest_text = ""
        final_text = ""

        async def worker_progress(payload: dict[str, Any]) -> None:
            enriched = {**payload, "agent": "worker"}
            await _emit_progress(progress_callback, enriched)

            phase = str(payload.get("phase") or "")
            if phase == "tool_start":
                tool_name = str(payload.get("name") or "tool")
                await emit_message(
                    from_agent="worker",
                    to_agent="manager",
                    kind="tool_intent",
                    summary=f"Starting tool: {tool_name}",
                    payload={
                        "name": tool_name,
                        "args": payload.get("args", {}),
                        "call_id": payload.get("call_id"),
                    },
                    visibility="user_visible",
                )
            elif phase == "tool_end":
                trace = payload.get("trace")
                if isinstance(trace, dict):
                    ok = bool(trace.get("ok", False))
                    tool_name = str(trace.get("name") or "tool")
                    await emit_message(
                        from_agent="worker",
                        to_agent="manager",
                        kind="tool_result",
                        summary=(
                            f"Completed tool: {tool_name}"
                            if ok
                            else f"Tool failed: {tool_name}"
                        ),
                        payload={
                            "trace": trace,
                            "call_id": payload.get("call_id"),
                        },
                        visibility="user_visible",
                        priority="high" if not ok else "normal",
                    )
            elif phase == "thinking":
                status_text = str(payload.get("status_text") or "").strip()
                if status_text:
                    await emit_message(
                        from_agent="worker",
                        to_agent="manager",
                        kind="plan_update",
                        summary=status_text,
                        payload={
                            "detail_text": payload.get("detail_text"),
                            "loop": payload.get("loop"),
                        },
                        visibility="internal",
                    )
            elif phase in {"error", "stopped"}:
                await emit_message(
                    from_agent="worker",
                    to_agent="manager",
                    kind="blocker",
                    summary=(
                        str(payload.get("error") or "")
                        or str(payload.get("reason") or "Worker halted.")
                    ),
                    payload=payload,
                    visibility="user_visible",
                    priority="urgent",
                )

        worker_brief = str(intent_snapshot.get("worker_brief") or user_message).strip()
        worker_brief = worker_brief or user_message
        max_rounds = 1 + self.manager_refine_rounds
        for round_index in range(max_rounds):
            await emit_message(
                from_agent="manager",
                to_agent="worker",
                kind="decision",
                summary=(
                    "Execute initial brief."
                    if round_index == 0
                    else f"Refinement cycle {round_index}: execute updated brief."
                ),
                payload={
                    "round": round_index + 1,
                    "worker_brief": worker_brief,
                    "acceptance_criteria": intent_snapshot.get(
                        "acceptance_criteria", []
                    ),
                },
                visibility="internal",
            )

            worker_result = await self._run_worker_turn(
                ctx=ctx,
                project_root=str(project_path),
                history=history,
                user_message=worker_brief,
                selected_targets=selected_targets,
                previous_response_id=worker_response_id,
                tool_memory=tool_memory,
                progress_callback=worker_progress,
                consume_steering_messages=consume_steering_messages,
                actor="worker",
            )
            all_traces.extend(worker_result.tool_traces)
            worker_response_id = worker_result.response_id or worker_response_id
            worker_skill_state = dict(worker_result.skill_state)
            worker_latest_text = worker_result.text
            context_metrics[f"worker_round_{round_index + 1}"] = (
                worker_result.context_metrics
            )

            await emit_message(
                from_agent="worker",
                to_agent="manager",
                kind="result_bundle",
                summary=trim_single_line(worker_result.text, 140),
                payload={
                    "round": round_index + 1,
                    "text": worker_result.text,
                    "tool_trace_count": len(worker_result.tool_traces),
                },
                visibility="internal",
            )

            manager_review = await self._manager_review_result(
                user_message=user_message,
                intent_snapshot=intent_snapshot,
                worker_text=worker_result.text,
                tool_traces=worker_result.tool_traces,
                progress_callback=progress_callback,
            )
            final_text = str(manager_review.get("final_response") or "").strip()
            decision = str(manager_review.get("decision") or "accept").lower().strip()
            refinement_brief = str(
                manager_review.get("refinement_brief") or ""
            ).strip()

            await emit_message(
                from_agent="manager",
                to_agent="worker",
                kind="decision",
                summary=(
                    "Accepted worker output."
                    if decision != "refine"
                    else "Requested refinement."
                ),
                payload={
                    "decision": decision,
                    "refinement_brief": refinement_brief,
                    "completion_summary": manager_review.get("completion_summary"),
                    "round": round_index + 1,
                },
                visibility="internal",
            )

            if decision != "refine":
                break
            if not refinement_brief:
                break
            worker_brief = refinement_brief
        else:
            final_text = worker_latest_text

        if not final_text:
            final_text = worker_latest_text or "Completed."

        await emit_message(
            from_agent="manager",
            to_agent="user",
            kind="final_response",
            summary=trim_single_line(final_text, 140),
            payload={"text": final_text},
            visibility="user_visible",
            priority="high",
        )

        return AgentTurnResult(
            text=final_text,
            tool_traces=all_traces,
            model=f"{self.manager_model}+{self.model}",
            response_id=worker_response_id,
            skill_state=worker_skill_state,
            context_metrics=context_metrics,
            agent_messages=emitted_messages,
        )

    def _new_peer_message(
        self,
        *,
        thread_id: str,
        from_agent: str,
        to_agent: str,
        kind: str,
        summary: str,
        payload: dict[str, Any],
        visibility: str = "internal",
        priority: str = "normal",
        requires_ack: bool = False,
        correlation_id: str | None = None,
        parent_id: str | None = None,
    ) -> AgentPeerMessage:
        return AgentPeerMessage(
            message_id=f"msg-{uuid.uuid4().hex[:16]}",
            thread_id=thread_id,
            from_agent=from_agent,
            to_agent=to_agent,
            kind=kind,
            summary=summary,
            payload=payload,
            visibility=visibility,
            priority=priority,
            requires_ack=requires_ack,
            correlation_id=correlation_id,
            parent_id=parent_id,
        )

    async def _manager_build_plan(
        self,
        *,
        project_path: Path,
        selected_targets: list[str],
        user_message: str,
        history: list[dict[str, str]],
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Any]:
        await _emit_progress(
            progress_callback,
            {
                "phase": "thinking",
                "status_text": "Manager planning",
                "detail_text": "Converting user request into worker brief",
                "agent": "manager",
            },
        )
        history_summary = _summarize_history_for_manager(history)
        payload = {
            "model": self.manager_model,
            "input": [
                {
                    "role": "user",
                    "content": (
                        f"Project root: {project_path}\n"
                        f"Selected targets: {selected_targets or []}\n"
                        f"Recent history:\n{history_summary}\n\n"
                        f"User request:\n{_trim_user_message(user_message, 6000)}"
                    ),
                }
            ],
            "instructions": _MANAGER_PLANNER_PROMPT,
            "truncation": "auto",
        }
        response = await self._responses_create(
            payload,
            telemetry={"api_retry_count": 0},
            progress_callback=progress_callback,
        )
        text = _extract_text(response)
        parsed = _extract_json_object(text)
        constraints = _normalize_string_list(parsed.get("constraints"))
        acceptance_criteria = _normalize_string_list(
            parsed.get("acceptance_criteria")
        )
        checkpoints = _normalize_string_list(parsed.get("checkpoints"))
        intent_summary = str(parsed.get("intent_summary") or "").strip()
        objective = str(parsed.get("objective") or "").strip()
        worker_brief = str(parsed.get("worker_brief") or "").strip()

        fallback_brief = _trim_user_message(user_message, 6000)
        return {
            "intent_summary": intent_summary or "Prepared execution brief.",
            "objective": objective or fallback_brief,
            "constraints": constraints,
            "acceptance_criteria": acceptance_criteria,
            "worker_brief": worker_brief or fallback_brief,
            "checkpoints": checkpoints,
            "selected_targets": selected_targets,
            "project_root": str(project_path),
        }

    async def _manager_review_result(
        self,
        *,
        user_message: str,
        intent_snapshot: dict[str, Any],
        worker_text: str,
        tool_traces: list[ToolTrace],
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Any]:
        await _emit_progress(
            progress_callback,
            {
                "phase": "thinking",
                "status_text": "Manager review",
                "detail_text": "Validating worker output against acceptance criteria",
                "agent": "manager",
            },
        )
        traces_summary = _summarize_tool_traces_for_manager(tool_traces, limit=24)
        payload = {
            "model": self.manager_model,
            "input": [
                {
                    "role": "user",
                    "content": (
                        f"Original user request:\n{_trim_user_message(user_message, 4000)}\n\n"
                        f"Intent snapshot:\n{json.dumps(intent_snapshot, ensure_ascii=False)}\n\n"
                        f"Worker output:\n{_trim_user_message(worker_text, 6000)}\n\n"
                        f"Tool trace summary:\n{traces_summary}"
                    ),
                }
            ],
            "instructions": _MANAGER_REVIEW_PROMPT,
            "truncation": "auto",
        }
        response = await self._responses_create(
            payload,
            telemetry={"api_retry_count": 0},
            progress_callback=progress_callback,
        )
        text = _extract_text(response)
        parsed = _extract_json_object(text)
        decision = str(parsed.get("decision") or "accept").strip().lower()
        if decision not in {"accept", "refine"}:
            decision = "accept"
        return {
            "decision": decision,
            "refinement_brief": str(parsed.get("refinement_brief") or "").strip(),
            "final_response": str(parsed.get("final_response") or "").strip()
            or worker_text,
            "completion_summary": str(parsed.get("completion_summary") or "").strip(),
        }

    async def _build_context(
        self,
        *,
        project_root: Path,
        selected_targets: list[str],
    ) -> str:
        files = await self._list_files(project_root)
        active = await self._active_builds(project_root)
        recent = await self._recent_builds(project_root)
        bom_targets = await self._bom_targets(project_root)
        variables_targets = await self._variables_targets(project_root)

        lines: list[str] = [
            "Project summary:",
            f"- root: {project_root}",
            f"- selected_targets: {selected_targets}",
            f"- context_files_count: {len(files)}",
            "- files:",
        ]
        lines.extend([f"  - {path}" for path in files[:120]])

        lines.append("- active_builds:")
        if active:
            for build in active:
                build_line = (
                    f"  - {build.get('build_id')} "
                    f"{build.get('target')} {build.get('status')}"
                )
                lines.append(build_line)
        else:
            lines.append("  - none")

        lines.append("- recent_builds:")
        if recent:
            for build in recent:
                lines.append(
                    "  - "
                    f"{build.get('build_id')} {build.get('target')} "
                    f"{build.get('status')} "
                    f"errors={build.get('errors')} "
                    f"warnings={build.get('warnings')}"
                )
        else:
            lines.append("  - none")

        lines.append("- report_targets:")
        lines.append(f"  - bom: {bom_targets if bom_targets else ['none']}")
        lines.append(
            f"  - variables: {variables_targets if variables_targets else ['none']}"
        )

        return "\n".join(lines)

    async def _list_files(self, project_root: Path) -> list[str]:
        return await asyncio.to_thread(policy.list_context_files, project_root, 240)

    async def _active_builds(self, project_root: Path) -> list[dict[str, Any]]:
        summary = await asyncio.to_thread(builds_domain.handle_get_active_builds)
        builds = summary.get("builds", []) if isinstance(summary, dict) else []
        return [
            build
            for build in builds
            if str(build.get("project_root", "")) == str(project_root)
        ]

    async def _recent_builds(self, project_root: Path) -> list[dict[str, Any]]:
        payload = await asyncio.to_thread(
            builds_domain.handle_get_build_history,
            str(project_root),
            None,
            20,
        )
        if not isinstance(payload, dict):
            return []
        raw_builds = payload.get("builds", [])
        if not isinstance(raw_builds, list):
            return []

        recent: list[dict[str, Any]] = []
        for build in raw_builds:
            if not isinstance(build, dict):
                continue
            recent.append(
                {
                    "build_id": build.get("buildId") or build.get("build_id"),
                    "target": build.get("target"),
                    "status": build.get("status"),
                    "errors": build.get("errors", 0),
                    "warnings": build.get("warnings", 0),
                }
            )
            if len(recent) >= 8:
                break
        return recent

    async def _bom_targets(self, project_root: Path) -> list[str]:
        payload = await asyncio.to_thread(
            artifacts_domain.handle_get_bom_targets,
            str(project_root),
        )
        if not isinstance(payload, dict):
            return []
        targets = payload.get("targets")
        if not isinstance(targets, list):
            return []
        return [str(target) for target in targets if isinstance(target, str)]

    async def _variables_targets(self, project_root: Path) -> list[str]:
        payload = await asyncio.to_thread(
            artifacts_domain.handle_get_variables_targets,
            str(project_root),
        )
        if not isinstance(payload, dict):
            return []
        targets = payload.get("targets")
        if not isinstance(targets, list):
            return []
        return [str(target) for target in targets if isinstance(target, str)]

    async def _responses_create_with_context_control(
        self,
        *,
        payload: dict[str, Any],
        telemetry: dict[str, Any],
        progress_callback: ProgressCallback | None,
        enable_preflight: bool = True,
    ) -> dict[str, Any]:
        if enable_preflight:
            preflight_tokens = await self._count_input_tokens(payload)
            telemetry["preflight_input_tokens"] = preflight_tokens
            if (
                isinstance(preflight_tokens, int)
                and preflight_tokens > self.context_hard_max_tokens
            ):
                previous_response_id = payload.get("previous_response_id")
                if isinstance(previous_response_id, str) and previous_response_id:
                    await _emit_progress(
                        progress_callback,
                        {
                            "phase": "compacting",
                            "status_text": "Compacting context",
                            "detail_text": "Input token budget exceeded",
                        },
                    )
                    compacted_id = await self._compact_previous_response(
                        previous_response_id=previous_response_id,
                        telemetry=telemetry,
                    )
                    if compacted_id:
                        payload = dict(payload)
                        payload["previous_response_id"] = compacted_id
                        preflight_tokens_after = await self._count_input_tokens(payload)
                        telemetry["preflight_input_tokens"] = preflight_tokens_after
                        if (
                            isinstance(preflight_tokens_after, int)
                            and preflight_tokens_after > self.context_hard_max_tokens
                        ):
                            raise RuntimeError(
                                "Request context remains too large after compaction. "
                                "Try a narrower request."
                            )
                else:
                    raise RuntimeError(
                        "Request context is too large for the model context window. "
                        "Please try a narrower request."
                    )

        return await self._responses_create(
            payload,
            telemetry=telemetry,
            progress_callback=progress_callback,
        )

    async def _responses_create(
        self,
        payload: dict[str, Any],
        *,
        telemetry: dict[str, Any] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        working_payload = dict(payload)
        compacted_once = False
        function_output_shrink_steps = (5000, 2500, 1200, 600, 300)
        function_output_shrink_index = 0
        for attempt in range(self.api_retries + 1):
            try:
                response = await client.responses.create(**working_payload)
                break
            except APIStatusError as exc:
                status_code = getattr(exc, "status_code", "unknown")
                should_retry = status_code == 429 and attempt < self.api_retries
                if should_retry:
                    if telemetry is not None:
                        telemetry["api_retry_count"] = (
                            int(telemetry.get("api_retry_count", 0)) + 1
                        )
                    delay_s = _compute_rate_limit_retry_delay_s(
                        exc=exc,
                        attempt=attempt,
                        base_delay_s=self.api_retry_base_delay_s,
                        max_delay_s=self.api_retry_max_delay_s,
                    )
                    await _emit_progress(
                        progress_callback,
                        {
                            "phase": "thinking",
                            "status_text": "Retrying model request",
                            "detail_text": f"Rate limited, retrying in {delay_s:.1f}s",
                        },
                    )
                    await asyncio.sleep(delay_s)
                    continue

                if _is_context_length_exceeded(
                    exc
                ) and _payload_has_function_call_outputs(working_payload):
                    if function_output_shrink_index < len(function_output_shrink_steps):
                        max_chars = function_output_shrink_steps[
                            function_output_shrink_index
                        ]
                        function_output_shrink_index += 1
                        reduced_payload = _shrink_function_call_outputs_payload(
                            working_payload,
                            max_chars=max_chars,
                        )
                        if reduced_payload is not None:
                            await _emit_progress(
                                progress_callback,
                                {
                                    "phase": "compacting",
                                    "status_text": "Compacting tool results",
                                    "detail_text": (
                                        "Reducing tool output size to continue"
                                    ),
                                },
                            )
                            working_payload = reduced_payload
                            continue
                    raise RuntimeError(
                        "Tool outputs are too large for the model context window. "
                        "Try a narrower request or fewer high-volume tools."
                    ) from exc

                if (
                    _is_context_length_exceeded(exc)
                    and not compacted_once
                    and isinstance(working_payload.get("previous_response_id"), str)
                    and working_payload.get("previous_response_id")
                ):
                    compacted_once = True
                    compacted_id = await self._compact_previous_response(
                        previous_response_id=str(
                            working_payload["previous_response_id"]
                        ),
                        telemetry=telemetry,
                    )
                    if compacted_id:
                        working_payload["previous_response_id"] = compacted_id
                        continue
                snippet = _extract_sdk_error_text(exc)[:500]
                raise RuntimeError(
                    f"Model API request failed ({status_code}): {snippet}"
                ) from exc
            except (APIConnectionError, APITimeoutError) as exc:
                if attempt < self.api_retries:
                    if telemetry is not None:
                        telemetry["api_retry_count"] = (
                            int(telemetry.get("api_retry_count", 0)) + 1
                        )
                    delay_s = _compute_network_retry_delay_s(
                        attempt=attempt,
                        base_delay_s=self.api_retry_base_delay_s,
                        max_delay_s=self.api_retry_max_delay_s,
                    )
                    await _emit_progress(
                        progress_callback,
                        {
                            "phase": "thinking",
                            "status_text": "Retrying model request",
                            "detail_text": (
                                f"Connection issue, retrying in {delay_s:.1f}s"
                            ),
                        },
                    )
                    await asyncio.sleep(delay_s)
                    continue
                raise RuntimeError(f"Model API request failed: {exc}") from exc

        body = _response_model_to_dict(response)
        if not isinstance(body, dict):
            raise RuntimeError("Model API returned non-object response")
        return body

    async def _count_input_tokens(self, payload: dict[str, Any]) -> int | None:
        client = self._get_client()
        count_payload = {
            "model": payload.get("model", self.model),
            "input": payload.get("input"),
            "instructions": payload.get("instructions"),
            "previous_response_id": payload.get("previous_response_id"),
            "tools": payload.get("tools"),
            "tool_choice": payload.get("tool_choice"),
            "truncation": payload.get("truncation", "disabled"),
        }
        try:
            counted = await client.responses.input_tokens.count(**count_payload)
        except Exception:
            return None
        body = _response_model_to_dict(counted)
        tokens = body.get("input_tokens")
        if isinstance(tokens, int):
            return tokens
        return None

    async def _compact_previous_response(
        self,
        *,
        previous_response_id: str,
        telemetry: dict[str, Any] | None = None,
    ) -> str | None:
        client = self._get_client()
        try:
            compacted = await client.responses.compact(
                model=self.model,
                previous_response_id=previous_response_id,
            )
        except APIStatusError:
            return None
        except (APIConnectionError, APITimeoutError):
            return None
        body = _response_model_to_dict(compacted)
        compacted_id = body.get("id")
        if isinstance(compacted_id, str) and compacted_id:
            if telemetry is not None:
                events = telemetry.setdefault("compaction_events", [])
                if isinstance(events, list):
                    events.append(
                        {
                            "from_response_id": previous_response_id,
                            "compacted_response_id": compacted_id,
                        }
                    )
            return compacted_id
        return None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout_s,
            )
        return self._client


def _response_model_to_dict(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        body = model_dump(mode="python")
        if isinstance(body, dict):
            return body
    to_dict = getattr(response, "to_dict", None)
    if callable(to_dict):
        body = to_dict()
        if isinstance(body, dict):
            return body
    raise RuntimeError("Model API returned unsupported response object")


def _extract_sdk_error_text(exc: APIStatusError) -> str:
    response = getattr(exc, "response", None)
    text = getattr(response, "text", None)
    if isinstance(text, str) and text:
        return text

    body = getattr(exc, "body", None)
    if body is not None:
        try:
            return json.dumps(body)
        except TypeError:
            return str(body)

    return str(exc)


def _compute_rate_limit_retry_delay_s(
    *,
    exc: APIStatusError,
    attempt: int,
    base_delay_s: float,
    max_delay_s: float,
) -> float:
    hinted_delay_s = _extract_retry_after_delay_s(exc)
    if hinted_delay_s is not None:
        return min(max_delay_s, max(0.05, hinted_delay_s))
    backoff_delay_s = max(0.05, base_delay_s) * (2 ** max(0, attempt))
    return min(max_delay_s, backoff_delay_s)


def _compute_network_retry_delay_s(
    *,
    attempt: int,
    base_delay_s: float,
    max_delay_s: float,
) -> float:
    backoff_delay_s = max(0.05, base_delay_s) * (2 ** max(0, attempt))
    return min(max_delay_s, backoff_delay_s)


def _extract_retry_after_delay_s(exc: APIStatusError) -> float | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is not None:
        retry_after_ms_raw = headers.get("retry-after-ms")
        retry_after_ms = _parse_positive_float(retry_after_ms_raw)
        if retry_after_ms is not None:
            return retry_after_ms / 1000.0

        retry_after_raw = headers.get("retry-after")
        retry_after_s = _parse_positive_float(retry_after_raw)
        if retry_after_s is not None:
            return retry_after_s

    message = _extract_sdk_error_text(exc)
    match = _RETRY_AFTER_TEXT_PATTERN.search(message)
    if match is None:
        return None

    value = _parse_positive_float(match.group(1))
    if value is None:
        return None

    unit = (match.group(2) or "").lower()
    if unit == "ms":
        return value / 1000.0
    return value


def _parse_positive_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(str(value).strip())
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed


def _is_context_length_exceeded(exc: APIStatusError) -> bool:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            code = error.get("code")
            if code == "context_length_exceeded":
                return True
    text = _extract_sdk_error_text(exc).lower()
    return "context_length_exceeded" in text or "context window" in text


def _build_turn_instructions(
    *,
    include_session_primer: bool,
    project_root: Path,
    selected_targets: list[str],
    skill_block: str,
    max_chars: int,
) -> str:
    chunks = [_SYSTEM_PROMPT]
    if include_session_primer:
        chunks.append(
            _build_session_primer(
                project_root=project_root,
                selected_targets=selected_targets,
            )
        )
    if skill_block.strip():
        chunks.append(skill_block)
    joined = "\n\n".join(chunks)
    return _truncate_middle(joined, max_chars)


def _build_prompt_cache_key(
    *,
    project_path: Path,
    tool_defs: list[dict[str, Any]],
    skill_state: dict[str, Any],
    model: str,
) -> str:
    tool_names = ",".join(
        sorted(
            str(tool.get("name", "")) for tool in tool_defs if isinstance(tool, dict)
        )
    )
    skill_ids = ",".join(
        str(value)
        for value in skill_state.get("selected_skill_ids", [])
        if isinstance(value, str)
    )
    digest_input = f"{project_path}|{model}|{tool_names}|{skill_ids}"
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:24]
    return f"atopile-agent:{digest}"


def _trim_user_message(message: str, max_chars: int) -> str:
    stripped = message.strip()
    if len(stripped) <= max_chars:
        return stripped
    if max_chars < 64:
        return stripped[:max_chars]
    head_chars = int(max_chars * 0.7)
    tail_chars = max_chars - head_chars - 17
    tail_chars = max(tail_chars, 32)
    return (
        stripped[:head_chars].rstrip()
        + "\n\n...[message truncated]...\n\n"
        + stripped[-tail_chars:].lstrip()
    )


def _consume_steering_updates(
    consume_steering_messages: SteeringMessagesCallback | None,
) -> list[str]:
    if consume_steering_messages is None:
        return []
    try:
        raw_messages = consume_steering_messages()
    except Exception:
        return []
    if not isinstance(raw_messages, list):
        return []

    normalized: list[str] = []
    for raw_message in raw_messages:
        if not isinstance(raw_message, str):
            continue
        stripped = raw_message.strip()
        if not stripped:
            continue
        normalized.append(_trim_user_message(stripped, 2000))
    return normalized


def _build_steering_inputs_for_model(messages: list[str]) -> list[dict[str, Any]]:
    if not messages:
        return []
    bullets = "\n".join(f"- {message}" for message in messages)
    return [
        {
            "role": "user",
            "content": (
                "Steering update while you are working. Keep progress so far, "
                "but adapt your plan using this guidance when feasible:\n"
                f"{bullets}"
            ),
        }
    ]


def _truncate_middle(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars < 64:
        return text[:max_chars]
    head_chars = int(max_chars * 0.65)
    tail_chars = max_chars - head_chars - 17
    tail_chars = max(tail_chars, 24)
    return (
        text[:head_chars].rstrip()
        + "\n\n...[truncated]...\n\n"
        + text[-tail_chars:].lstrip()
    )


def _limit_tool_output_for_model(
    value: dict[str, Any],
    *,
    max_chars: int,
) -> dict[str, Any]:
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return value

    if len(serialized) <= max_chars:
        return value

    keep_keys = {
        "error",
        "error_type",
        "success",
        "message",
        "path",
        "build_id",
        "target",
        "found",
        "openai_file_id",
        "lcsc_id",
        "operations_applied",
        "first_changed_line",
        "total",
        "count",
    }
    compact: dict[str, Any] = {key: value[key] for key in keep_keys if key in value}
    compact["truncated"] = True
    compact["truncated_reason"] = "tool_output_budget_exceeded"
    compact["original_size_chars"] = len(serialized)
    compact["top_level_keys"] = list(value.keys())[:30]
    compact["preview"] = serialized[: min(1200, max(200, max_chars // 2))]
    return compact


def _extract_function_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    output = response.get("output", [])
    if not isinstance(output, list):
        return []
    return [
        item
        for item in output
        if isinstance(item, dict) and item.get("type") == "function_call"
    ]


def _extract_text(response: dict[str, Any]) -> str:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    pieces: list[str] = []
    output = response.get("output", [])
    if not isinstance(output, list):
        return ""

    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        content = item.get("content", [])
        if not isinstance(content, list):
            continue
        for content_item in content:
            if not isinstance(content_item, dict):
                continue
            if content_item.get("type") in {"output_text", "text"}:
                text = content_item.get("text")
                if isinstance(text, str) and text.strip():
                    pieces.append(text.strip())

    return "\n\n".join(pieces)


async def _emit_progress(
    callback: ProgressCallback | None,
    payload: dict[str, Any],
) -> None:
    if callback is None:
        return

    maybe_awaitable = callback(payload)
    if inspect.isawaitable(maybe_awaitable):
        await maybe_awaitable


def _sanitize_tool_output_for_model(value: Any) -> Any:
    """Remove UI-only/internal keys before returning tool output to model."""
    if isinstance(value, dict):
        return {
            key: _sanitize_tool_output_for_model(item)
            for key, item in value.items()
            if not str(key).startswith("_")
        }
    if isinstance(value, list):
        return [_sanitize_tool_output_for_model(item) for item in value]
    return value


def _build_function_call_outputs_for_model(
    *,
    call_id: str,
    tool_name: str,
    result_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = [
        {
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps(result_payload),
        }
    ]

    if tool_name == "parts_install":
        if not bool(result_payload.get("success", False)):
            return outputs

        lcsc_id = result_payload.get("lcsc_id")
        lcsc_suffix = (
            f" lcsc_id={lcsc_id};" if isinstance(lcsc_id, str) and lcsc_id else ""
        )
        outputs.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "parts_install completed."
                            f"{lcsc_suffix} "
                            "If this is a complex part (MCU/sensor/PMIC/radio), "
                            "call datasheet_read next to verify recommended "
                            "application circuitry and pin constraints."
                        ),
                    }
                ],
            }
        )
        return outputs

    if tool_name != "datasheet_read":
        return outputs

    file_id = result_payload.get("openai_file_id")
    if not isinstance(file_id, str) or not file_id:
        return outputs

    details: list[str] = []
    source = result_payload.get("source")
    if isinstance(source, str) and source:
        details.append(f"source={source}")
    filename = result_payload.get("filename")
    if isinstance(filename, str) and filename:
        details.append(f"filename={filename}")
    query = result_payload.get("query")
    if isinstance(query, str) and query:
        details.append(f"focus_query={query}")

    detail_text = ", ".join(details) if details else "no metadata"
    outputs.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "datasheet_read attached a datasheet PDF. "
                        f"file_id={file_id}; {detail_text}. "
                        "Use this file for datasheet analysis."
                    ),
                },
                {
                    "type": "input_file",
                    "file_id": file_id,
                },
            ],
        }
    )
    return outputs


def _payload_has_function_call_outputs(payload: dict[str, Any]) -> bool:
    raw_input = payload.get("input")
    if not isinstance(raw_input, list):
        return False
    return any(
        isinstance(item, dict) and item.get("type") == "function_call_output"
        for item in raw_input
    )


def _shrink_function_call_outputs_payload(
    payload: dict[str, Any],
    *,
    max_chars: int,
) -> dict[str, Any] | None:
    raw_input = payload.get("input")
    if not isinstance(raw_input, list):
        return None

    changed = False
    next_input: list[Any] = []
    for item in raw_input:
        if not (isinstance(item, dict) and item.get("type") == "function_call_output"):
            next_input.append(item)
            continue

        output = item.get("output")
        if not isinstance(output, str):
            next_input.append(item)
            continue

        shrunk_output = _shrink_function_call_output_string(
            output,
            max_chars=max_chars,
        )
        if shrunk_output != output:
            changed = True
            next_item = dict(item)
            next_item["output"] = shrunk_output
            next_input.append(next_item)
        else:
            next_input.append(item)

    if not changed:
        return None

    next_payload = dict(payload)
    next_payload["input"] = next_input
    return next_payload


def _shrink_function_call_output_string(
    output: str,
    *,
    max_chars: int,
) -> str:
    if len(output) <= max_chars:
        return output

    try:
        parsed = json.loads(output)
    except Exception:
        return _truncate_middle(output, max_chars)

    if isinstance(parsed, dict):
        compacted = _limit_tool_output_for_model(parsed, max_chars=max_chars)
        try:
            compacted_text = json.dumps(compacted, ensure_ascii=False, default=str)
        except Exception:
            return _truncate_middle(output, max_chars)
        if len(compacted_text) <= max_chars:
            return compacted_text
        return _truncate_middle(compacted_text, max_chars)

    return _truncate_middle(output, max_chars)
