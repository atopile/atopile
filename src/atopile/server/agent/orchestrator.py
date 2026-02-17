"""Server-side agent orchestration with strict tool execution."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from atopile.dataclasses import AppContext
from atopile.model import builds as builds_domain
from atopile.server.agent import policy, tools
from atopile.server.agent.orchestrator_helpers import (
    _allocate_fixed_skill_char_caps,
    _build_execution_guard_inputs_for_model,
    _build_function_call_outputs_for_model,
    _build_prompt_cache_key,
    _build_steering_inputs_for_model,
    _build_worker_failure_streak_stop_text,
    _build_worker_loop_guard_message,
    _build_worker_loop_guard_stop_text,
    _build_worker_no_progress_stop_text,
    _build_worker_time_budget_stop_text,
    _compute_network_retry_delay_s,
    _compute_rate_limit_retry_delay_s,
    _consume_steering_updates,
    _extract_function_calls,
    _extract_sdk_error_text,
    _extract_text,
    _emit_progress,
    _emit_trace,
    _is_context_length_exceeded,
    _limit_tool_output_for_model,
    _loop_has_concrete_progress,
    _parse_fixed_skill_token_budgets,
    _payload_debug_summary,
    _payload_has_function_call_outputs,
    _response_model_to_dict,
    _sanitize_tool_output_for_model,
    _shrink_function_call_outputs_payload,
    _summarize_response_for_trace,
    _summarize_function_call_for_trace,
    _summarize_tool_result_for_trace,
    _tool_call_signature,
    _to_trace_preview,
    _trim_user_message,
    _truncate_middle,
)
from atopile.server.agent.orchestrator_prompt import SYSTEM_PROMPT
from atopile.server.domains import artifacts as artifacts_domain

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]
SteeringMessagesCallback = Callable[[], list[str]]
MessageCallback = Callable[[dict[str, Any]], Awaitable[None] | None]
TraceCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]
_TRACE_DISABLE_VALUES = {"0", "false", "no", "off"}


def _remap_hashline_anchor(
    raw_anchor: Any,
    remaps: dict[str, str],
) -> tuple[Any, bool]:
    if not isinstance(raw_anchor, str):
        return raw_anchor, False
    prefix, sep, suffix = raw_anchor.partition("|")
    mapped = remaps.get(prefix.strip().lower())
    if not isinstance(mapped, str) or not mapped:
        return raw_anchor, False
    if sep:
        return f"{mapped}|{suffix}", True
    return mapped, True


def _apply_project_edit_remaps(
    arguments: dict[str, Any],
    remaps: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    normalized_remaps = {
        str(key).strip().lower(): str(value).strip()
        for key, value in remaps.items()
        if str(key).strip() and str(value).strip()
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

        set_line = edit.get("set_line")
        if isinstance(set_line, dict):
            updated = dict(set_line)
            remapped_anchor, remapped = _remap_hashline_anchor(
                updated.get("anchor"),
                normalized_remaps,
            )
            if remapped:
                updated["anchor"] = remapped_anchor
                changed = True
            edit["set_line"] = updated

        replace_lines = edit.get("replace_lines")
        if isinstance(replace_lines, dict):
            updated = dict(replace_lines)
            for key in ("start_anchor", "end_anchor"):
                remapped_anchor, remapped = _remap_hashline_anchor(
                    updated.get(key),
                    normalized_remaps,
                )
                if remapped:
                    updated[key] = remapped_anchor
                    changed = True
            edit["replace_lines"] = updated

        insert_after = edit.get("insert_after")
        if isinstance(insert_after, dict):
            updated = dict(insert_after)
            remapped_anchor, remapped = _remap_hashline_anchor(
                updated.get("anchor"),
                normalized_remaps,
            )
            if remapped:
                updated["anchor"] = remapped_anchor
                changed = True
            edit["insert_after"] = updated

        updated_edits.append(edit)

    if not changed:
        return arguments, False

    updated_arguments["edits"] = updated_edits
    return updated_arguments, True


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
        "- package references: use package_ato_list/package_ato_search/\n"
        "  package_ato_read to mine installed package `.ato` sources for\n"
        "  reusable design patterns.\n"
        "- web research: use web_search for external/current facts when the\n"
        "  answer is not available in the project files.\n"
        "- reports: for BOM/parts lists use report_bom; for computed parameters\n"
        "  and constraints use report_variables.\n"
        "- manufacturing: use manufacturing_generate to create artifacts, then\n"
        "  build_logs_search to track, then manufacturing_summary to inspect.\n"
        "- pcb layout flow: manually place critical connectors/components first,\n"
        "  review with autolayout_request_screenshot until approved, then run\n"
        "  autolayout_run for placement.\n"
        "- placement/routing apply safety: monitor with autolayout_status and\n"
        "  call autolayout_fetch_to_layout only when state is\n"
        "  awaiting_selection/completed; if fetch says queued/running, wait the\n"
        "  suggested seconds and check status again.\n"
        "- after placement fetch: review with screenshots, then run\n"
        "  autolayout_run for routing and repeat status->fetch->review.\n"
        "- planes/stackup: use autolayout_configure_board_intent to encode\n"
        "  ground pour and stackup assumptions in ato.yaml before routing.\n"
        "- autolayout per-run cap: each placement/routing run is limited to\n"
        "  2 minutes. Use short iterative cycles: run, review candidates/screens,\n"
        "  then resume with resume_board_id when quality is insufficient.\n"
        "- quality loop: check in periodically with autolayout_status\n"
        "  (wait_seconds/poll_interval_seconds), and if quality is insufficient,\n"
        "  call autolayout_run with resume_board_id for another <=2 minute pass.\n"
        "- screenshots: use autolayout_request_screenshot (2d/3d), then\n"
        "  build_logs_search to track completion and read output paths.\n"
        "- crowded board review: use autolayout_request_screenshot with\n"
        "  highlight_components to spotlight one part and dim others.\n"
        "- manual moves: read placement_check from\n"
        "  layout_set_component_position to verify on-board status and\n"
        "  collisions immediately.\n"
        "- drc: use layout_run_drc after key placement/routing edits to get\n"
        "  KiCad rule errors/warnings before proceeding.\n"
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
class AgentTurnResult:
    text: str
    tool_traces: list[ToolTrace]
    model: str
    response_id: str | None = None
    skill_state: dict[str, Any] = field(default_factory=dict)
    context_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FixedSkillDoc:
    id: str
    path: Path
    body: str


class AgentOrchestrator:
    def __init__(self) -> None:
        self.base_url = os.getenv("ATOPILE_AGENT_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("ATOPILE_AGENT_MODEL", "gpt-5.1-codex-max")
        self.api_key = os.getenv("ATOPILE_AGENT_OPENAI_API_KEY") or os.getenv(
            "OPENAI_API_KEY"
        )
        self.timeout_s = float(os.getenv("ATOPILE_AGENT_TIMEOUT_S", "120"))
        self.max_tool_loops = int(os.getenv("ATOPILE_AGENT_MAX_TOOL_LOOPS", "240"))
        self.max_turn_seconds = float(
            os.getenv("ATOPILE_AGENT_MAX_TURN_SECONDS", "480")
        )
        self.max_turn_seconds = max(30.0, min(self.max_turn_seconds, 3_600.0))
        self.api_retries = int(os.getenv("ATOPILE_AGENT_API_RETRIES", "4"))
        self.api_retry_base_delay_s = float(
            os.getenv("ATOPILE_AGENT_API_RETRY_BASE_DELAY_S", "0.5")
        )
        self.api_retry_max_delay_s = float(
            os.getenv("ATOPILE_AGENT_API_RETRY_MAX_DELAY_S", "8.0")
        )
        default_skills_dir = (
            Path(__file__).resolve().parents[4] / ".claude" / "skills"
        )
        self.skills_dir = default_skills_dir
        self.fixed_skill_ids = ["agent", "ato"]
        self.fixed_skill_token_budgets = _parse_fixed_skill_token_budgets(
            os.getenv(
                "ATOPILE_AGENT_FIXED_SKILL_TOKEN_BUDGETS",
                "agent:10000,ato:40000",
            ),
            default_skill_ids=self.fixed_skill_ids,
        )
        self.fixed_skill_chars_per_token = float(
            os.getenv("ATOPILE_AGENT_FIXED_SKILL_CHARS_PER_TOKEN", "4.0")
        )
        self.fixed_skill_chars_per_token = max(
            1.0, min(self.fixed_skill_chars_per_token, 8.0)
        )
        self.fixed_skill_total_max_chars = int(
            os.getenv("ATOPILE_AGENT_FIXED_SKILL_TOTAL_MAX_CHARS", "220000")
        )
        self.prefix_max_chars = int(
            os.getenv("ATOPILE_AGENT_PREFIX_MAX_CHARS", "220000")
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
        raw_trace_enabled = os.getenv("ATOPILE_AGENT_TRACE_ENABLED", "1")
        self.trace_enabled = (
            str(raw_trace_enabled).strip().lower() not in _TRACE_DISABLE_VALUES
        )
        self.trace_preview_max_chars = int(
            os.getenv("ATOPILE_AGENT_TRACE_PREVIEW_MAX_CHARS", "4000")
        )
        self.trace_preview_max_chars = max(
            300, min(self.trace_preview_max_chars, 20000)
        )
        self.worker_loop_guard_window = int(
            os.getenv("ATOPILE_AGENT_WORKER_LOOP_GUARD_WINDOW", "8")
        )
        self.worker_loop_guard_window = max(4, min(self.worker_loop_guard_window, 24))
        self.worker_loop_guard_min_discovery = int(
            os.getenv("ATOPILE_AGENT_WORKER_LOOP_GUARD_MIN_DISCOVERY", "6")
        )
        self.worker_loop_guard_min_discovery = max(
            4, min(self.worker_loop_guard_min_discovery, 20)
        )
        self.worker_loop_guard_max_hits = int(
            os.getenv("ATOPILE_AGENT_WORKER_LOOP_GUARD_MAX_HITS", "3")
        )
        self.worker_loop_guard_max_hits = max(
            1, min(self.worker_loop_guard_max_hits, 8)
        )
        self.worker_failure_streak_limit = int(
            os.getenv("ATOPILE_AGENT_WORKER_FAILURE_STREAK_LIMIT", "6")
        )
        self.worker_failure_streak_limit = max(
            2, min(self.worker_failure_streak_limit, 20)
        )
        self.worker_no_progress_loop_limit = int(
            os.getenv("ATOPILE_AGENT_WORKER_NO_PROGRESS_LOOP_LIMIT", "18")
        )
        self.worker_no_progress_loop_limit = max(
            4, min(self.worker_no_progress_loop_limit, 60)
        )
        self._client: AsyncOpenAI | None = None

    def _load_required_skill_docs(self) -> list[FixedSkillDoc]:
        docs: list[FixedSkillDoc] = []
        missing: list[str] = []
        for skill_id in self.fixed_skill_ids:
            skill_path = self.skills_dir / skill_id / "SKILL.md"
            try:
                body = skill_path.read_text(encoding="utf-8").strip()
            except FileNotFoundError:
                missing.append(skill_id)
                continue
            if not body:
                missing.append(skill_id)
                continue
            docs.append(
                FixedSkillDoc(
                    id=skill_id,
                    path=skill_path,
                    body=body,
                )
            )

        if missing:
            missing_text = ", ".join(missing)
            raise RuntimeError(
                "Missing required fixed skill docs. "
                f"Expected ids: {self.fixed_skill_ids}. Missing: {missing_text}."
            )
        return docs

    def _render_fixed_skills_block(
        self,
        *,
        docs: list[FixedSkillDoc],
        per_skill_max_chars: dict[str, int],
    ) -> str:
        sections = ["ACTIVE SKILLS (FULL DOCS):"]
        for doc in docs:
            body = doc.body
            skill_cap = int(per_skill_max_chars.get(doc.id, 0))
            if skill_cap > 0:
                body = _truncate_middle(body, skill_cap)
            sections.append(
                "\n".join(
                    [
                        f"SKILL {doc.id}",
                        f"Source: {doc.path}",
                        body.strip(),
                    ]
                ).strip()
            )

        block = "\n\n".join(sections)
        return _truncate_middle(block, self.fixed_skill_total_max_chars)

    def _build_fixed_skill_state(
        self,
        *,
        docs: list[FixedSkillDoc],
        rendered_total_chars: int,
        per_skill_max_chars: dict[str, int],
    ) -> dict[str, Any]:
        return {
            "mode": "fixed",
            "skills_dir": str(self.skills_dir),
            "requested_skill_ids": list(self.fixed_skill_ids),
            "selected_skill_ids": [doc.id for doc in docs],
            "selected_skills": [
                {
                    "id": doc.id,
                    "path": str(doc.path),
                    "chars": len(doc.body),
                }
                for doc in docs
            ],
            "missing_skill_ids": [],
            "per_skill_max_chars": dict(per_skill_max_chars),
            "reasoning": [
                "mode=fixed",
                "selected_ids=" + ",".join(doc.id for doc in docs),
                f"rendered_chars={rendered_total_chars}",
                f"max_chars={self.fixed_skill_total_max_chars}",
            ],
            "total_chars": rendered_total_chars,
            "max_chars": self.fixed_skill_total_max_chars,
            "generated_at": time.time(),
        }

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
            message_callback=message_callback,
            trace_callback=trace_callback,
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
        message_callback: MessageCallback | None = None,
        trace_callback: TraceCallback | None = None,
    ) -> AgentTurnResult:
        _ = message_callback

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

        fixed_docs = self._load_required_skill_docs()

        per_skill_max_chars = _allocate_fixed_skill_char_caps(
            docs=fixed_docs,
            token_budgets=self.fixed_skill_token_budgets,
            chars_per_token=self.fixed_skill_chars_per_token,
            total_max_chars=self.fixed_skill_total_max_chars,
        )
        skill_block = self._render_fixed_skills_block(
            docs=fixed_docs,
            per_skill_max_chars=per_skill_max_chars,
        )
        skill_state = self._build_fixed_skill_state(
            docs=fixed_docs,
            rendered_total_chars=len(skill_block),
            per_skill_max_chars=per_skill_max_chars,
        )

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

        tool_defs = tools.get_tool_definitions()
        request_payload: dict[str, Any] = {
            "model": self.model,
            "input": request_input,
            "instructions": instructions,
            "tools": tool_defs,
            "tool_choice": "auto",
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
        await _emit_trace(
            trace_callback if self.trace_enabled else None,
            "turn_started",
            {
                "model": self.model,
                "project_root": str(project_path),
                "selected_targets": list(selected_targets or []),
                "history_items": len(history),
                "user_message_preview": _to_trace_preview(
                    trimmed_user_message,
                    max_chars=self.trace_preview_max_chars,
                ),
                "previous_response_id": previous_response_id,
                "tool_memory_keys": sorted((tool_memory or {}).keys()),
                "request_payload": _payload_debug_summary(request_payload),
            },
        )

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
            trace_callback=trace_callback if self.trace_enabled else None,
        )

        traces: list[ToolTrace] = []
        loops = 0
        last_response_id: str | None = response.get("id")
        recent_tool_signatures: list[str] = []
        loop_guard_hits = 0
        consecutive_tool_failures = 0
        no_progress_loops = 0
        started_at_s = time.monotonic()
        while loops < self.max_tool_loops:
            elapsed_s = time.monotonic() - started_at_s
            await _emit_trace(
                trace_callback if self.trace_enabled else None,
                "loop_started",
                {
                    "loop": loops + 1,
                    "elapsed_seconds": round(elapsed_s, 3),
                    "response_id": response.get("id"),
                },
            )
            if elapsed_s >= self.max_turn_seconds:
                await _emit_progress(
                    progress_callback,
                    {
                        "phase": "stopped",
                        "reason": "turn_time_budget_exceeded",
                        "loop": loops,
                        "tool_calls_total": len(traces),
                        "elapsed_seconds": round(elapsed_s, 1),
                    },
                )
                await _emit_trace(
                    trace_callback if self.trace_enabled else None,
                    "turn_stopped",
                    {
                        "reason": "turn_time_budget_exceeded",
                        "loop": loops,
                        "tool_calls_total": len(traces),
                        "elapsed_seconds": round(elapsed_s, 1),
                    },
                )
                return AgentTurnResult(
                    text=_build_worker_time_budget_stop_text(
                        traces=traces,
                        loops=loops,
                        elapsed_seconds=elapsed_s,
                    ),
                    tool_traces=traces,
                    model=self.model,
                    response_id=last_response_id,
                    skill_state=skill_state,
                    context_metrics=telemetry,
                )
            loops += 1
            function_calls = _extract_function_calls(response)
            await _emit_trace(
                trace_callback if self.trace_enabled else None,
                "loop_function_calls",
                {
                    "loop": loops,
                    "response_id": response.get("id"),
                    "function_call_count": len(function_calls),
                    "function_calls": [
                        _summarize_function_call_for_trace(
                            call,
                            max_chars=self.trace_preview_max_chars,
                        )
                        for call in function_calls
                    ],
                },
            )
            if not function_calls:
                steering_inputs = _build_steering_inputs_for_model(
                    _consume_steering_updates(consume_steering_messages)
                )
                if steering_inputs:
                    await _emit_trace(
                        trace_callback if self.trace_enabled else None,
                        "steering_applied",
                        {
                            "loop": loops,
                            "steering_items": len(steering_inputs),
                        },
                    )
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
                        trace_callback=trace_callback if self.trace_enabled else None,
                        enable_preflight=False,
                    )
                    last_response_id = response.get("id") or last_response_id
                    continue
                text = _extract_text(response)
                if not text:
                    text = "No assistant response produced."
                await _emit_trace(
                    trace_callback if self.trace_enabled else None,
                    "turn_completed",
                    {
                        "loop": loops,
                        "tool_calls_total": len(traces),
                        "response_id": response.get("id"),
                        "assistant_text_preview": _to_trace_preview(
                            text,
                            max_chars=self.trace_preview_max_chars,
                        ),
                    },
                )
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
            loop_traces: list[ToolTrace] = []
            tool_count = len(function_calls)
            for tool_index, call in enumerate(function_calls, start=1):
                call_id = call.get("call_id") or call.get("id")
                if not call_id:
                    await _emit_trace(
                        trace_callback if self.trace_enabled else None,
                        "tool_call_skipped",
                        {
                            "loop": loops,
                            "tool_index": tool_index,
                            "tool_count": tool_count,
                            "reason": "missing_call_id",
                            "call": _summarize_function_call_for_trace(
                                call,
                                max_chars=self.trace_preview_max_chars,
                            ),
                        },
                    )
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
                await _emit_trace(
                    trace_callback if self.trace_enabled else None,
                    "tool_call_started",
                    {
                        "loop": loops,
                        "tool_index": tool_index,
                        "tool_count": tool_count,
                        "call_id": str(call_id),
                        "name": tool_name,
                        "raw_arguments_preview": _to_trace_preview(
                            raw_args,
                            max_chars=self.trace_preview_max_chars,
                        ),
                        "parsed_arguments": (
                            parsed_args if parsed_args is not None else {}
                        ),
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
                    )
                except Exception as exc:
                    ok = False
                    args = parsed_args if parsed_args is not None else {}
                    remaps = getattr(exc, "remaps", None)
                    auto_remap_attempted = False
                    if tool_name == "project_edit_file" and isinstance(remaps, dict):
                        remapped_args, did_remap = _apply_project_edit_remaps(
                            args,
                            remaps,
                        )
                        if did_remap:
                            auto_remap_attempted = True
                            try:
                                result_payload = await tools.execute_tool(
                                    name=tool_name,
                                    arguments=remapped_args,
                                    project_root=project_path,
                                    ctx=ctx,
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
                loop_traces.append(traces[-1])
                if ok:
                    consecutive_tool_failures = 0
                else:
                    consecutive_tool_failures += 1
                recent_tool_signatures.append(
                    _tool_call_signature(tool_name=tool_name, args=args)
                )
                if len(recent_tool_signatures) > 48:
                    recent_tool_signatures = recent_tool_signatures[-48:]
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
                await _emit_trace(
                    trace_callback if self.trace_enabled else None,
                    "tool_call_completed",
                    {
                        "loop": loops,
                        "tool_index": tool_index,
                        "tool_count": tool_count,
                        "call_id": str(call_id),
                        "name": tool_name,
                        "ok": ok,
                        "arguments": args,
                        "result": _summarize_tool_result_for_trace(
                            result_payload,
                            max_chars=self.trace_preview_max_chars,
                        ),
                    },
                )
                if consecutive_tool_failures >= self.worker_failure_streak_limit:
                    telemetry["failure_streak"] = consecutive_tool_failures
                    await _emit_progress(
                        progress_callback,
                        {
                            "phase": "stopped",
                            "reason": "repeated_tool_failures",
                            "loop": loops,
                            "tool_calls_total": len(traces),
                            "failure_streak": consecutive_tool_failures,
                        },
                    )
                    await _emit_trace(
                        trace_callback if self.trace_enabled else None,
                        "turn_stopped",
                        {
                            "reason": "repeated_tool_failures",
                            "loop": loops,
                            "tool_calls_total": len(traces),
                            "failure_streak": consecutive_tool_failures,
                        },
                    )
                    return AgentTurnResult(
                        text=_build_worker_failure_streak_stop_text(
                            traces=traces,
                            loops=loops,
                            failure_streak=consecutive_tool_failures,
                        ),
                        tool_traces=traces,
                        model=self.model,
                        response_id=last_response_id,
                        skill_state=skill_state,
                        context_metrics=telemetry,
                    )
                output_count_before = len(outputs)
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
                await _emit_trace(
                    trace_callback if self.trace_enabled else None,
                    "function_call_output_built",
                    {
                        "loop": loops,
                        "call_id": str(call_id),
                        "tool_name": tool_name,
                        "output_items_added": len(outputs) - output_count_before,
                    },
                )

            steering_inputs = _build_steering_inputs_for_model(
                _consume_steering_updates(consume_steering_messages)
            )
            if _loop_has_concrete_progress(loop_traces):
                no_progress_loops = 0
            else:
                no_progress_loops += 1
            telemetry["no_progress_loops"] = no_progress_loops
            if steering_inputs:
                no_progress_loops = max(0, no_progress_loops - 1)
            guard_message = _build_worker_loop_guard_message(
                traces=traces,
                recent_tool_signatures=recent_tool_signatures,
                loops=loops,
                guard_hits=loop_guard_hits,
                window=self.worker_loop_guard_window,
                min_discovery=self.worker_loop_guard_min_discovery,
            )
            guard_inputs: list[dict[str, Any]] = []
            if guard_message:
                loop_guard_hits += 1
                telemetry["loop_guard_hits"] = loop_guard_hits
                guard_inputs = _build_execution_guard_inputs_for_model(guard_message)
                outputs.extend(guard_inputs)
                await _emit_progress(
                    progress_callback,
                    {
                        "phase": "thinking",
                        "status_text": "Execution nudge",
                        "detail_text": "Breaking repetitive discovery loop",
                        "loop": loops,
                        "tool_calls_total": len(traces),
                        "loop_guard_hits": loop_guard_hits,
                    },
                )
                await _emit_trace(
                    trace_callback if self.trace_enabled else None,
                    "loop_guard_triggered",
                    {
                        "loop": loops,
                        "tool_calls_total": len(traces),
                        "loop_guard_hits": loop_guard_hits,
                        "guard_message_preview": _to_trace_preview(
                            guard_message,
                            max_chars=self.trace_preview_max_chars,
                        ),
                    },
                )
                if loop_guard_hits > self.worker_loop_guard_max_hits:
                    await _emit_progress(
                        progress_callback,
                        {
                            "phase": "stopped",
                            "reason": "repetitive_discovery_loop",
                            "loop": loops,
                            "tool_calls_total": len(traces),
                        },
                    )
                    await _emit_trace(
                        trace_callback if self.trace_enabled else None,
                        "turn_stopped",
                        {
                            "reason": "repetitive_discovery_loop",
                            "loop": loops,
                            "tool_calls_total": len(traces),
                        },
                    )
                    return AgentTurnResult(
                        text=_build_worker_loop_guard_stop_text(
                            traces=traces,
                            loops=loops,
                        ),
                        tool_traces=traces,
                        model=self.model,
                        response_id=last_response_id,
                        skill_state=skill_state,
                        context_metrics=telemetry,
                    )
            if no_progress_loops >= self.worker_no_progress_loop_limit:
                await _emit_progress(
                    progress_callback,
                    {
                        "phase": "stopped",
                        "reason": "no_concrete_progress",
                        "loop": loops,
                        "tool_calls_total": len(traces),
                        "no_progress_loops": no_progress_loops,
                    },
                )
                await _emit_trace(
                    trace_callback if self.trace_enabled else None,
                    "turn_stopped",
                    {
                        "reason": "no_concrete_progress",
                        "loop": loops,
                        "tool_calls_total": len(traces),
                        "no_progress_loops": no_progress_loops,
                    },
                )
                return AgentTurnResult(
                    text=_build_worker_no_progress_stop_text(
                        traces=traces,
                        loops=loops,
                        no_progress_loops=no_progress_loops,
                    ),
                    tool_traces=traces,
                    model=self.model,
                    response_id=last_response_id,
                    skill_state=skill_state,
                    context_metrics=telemetry,
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
            elif guard_inputs:
                # Progress event already emitted for guard trigger; avoid noisy
                # "reviewing tool results" chatter on the same loop.
                pass
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
                trace_callback=trace_callback if self.trace_enabled else None,
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
        await _emit_trace(
            trace_callback if self.trace_enabled else None,
            "turn_stopped",
            {
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
        trace_callback: TraceCallback | None = None,
        enable_preflight: bool = True,
    ) -> dict[str, Any]:
        counted_preflight_tokens: int | None = None
        if enable_preflight:
            preflight_tokens = await self._count_input_tokens(payload)
            telemetry["preflight_input_tokens"] = preflight_tokens
            if isinstance(preflight_tokens, int):
                counted_preflight_tokens = preflight_tokens
            await _emit_trace(
                trace_callback if self.trace_enabled else None,
                "model_preflight_tokens",
                {
                    "input_tokens": preflight_tokens,
                    "payload": _payload_debug_summary(payload),
                },
            )
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
                            "input_tokens": preflight_tokens,
                            "context_limit_tokens": self.context_hard_max_tokens,
                        },
                    )
                    compacted_id = await self._compact_previous_response(
                        previous_response_id=previous_response_id,
                        telemetry=telemetry,
                    )
                    if compacted_id:
                        await _emit_trace(
                            trace_callback if self.trace_enabled else None,
                            "context_compacted",
                            {
                                "from_response_id": previous_response_id,
                                "compacted_response_id": compacted_id,
                            },
                        )
                        payload = dict(payload)
                        payload["previous_response_id"] = compacted_id
                        preflight_tokens_after = await self._count_input_tokens(payload)
                        telemetry["preflight_input_tokens"] = preflight_tokens_after
                        if isinstance(preflight_tokens_after, int):
                            counted_preflight_tokens = preflight_tokens_after
                        await _emit_trace(
                            trace_callback if self.trace_enabled else None,
                            "model_preflight_tokens",
                            {
                                "input_tokens": preflight_tokens_after,
                                "payload": _payload_debug_summary(payload),
                            },
                        )
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
            trace_callback=trace_callback if self.trace_enabled else None,
            preflight_input_tokens=counted_preflight_tokens,
            context_limit_tokens=self.context_hard_max_tokens,
        )

    async def _responses_create(
        self,
        payload: dict[str, Any],
        *,
        telemetry: dict[str, Any] | None = None,
        progress_callback: ProgressCallback | None = None,
        trace_callback: TraceCallback | None = None,
        preflight_input_tokens: int | None = None,
        context_limit_tokens: int | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        working_payload = dict(payload)
        compacted_once = False
        function_output_shrink_steps = (5000, 2500, 1200, 600, 300)
        function_output_shrink_index = 0
        for attempt in range(self.api_retries + 1):
            await _emit_trace(
                trace_callback if self.trace_enabled else None,
                "model_request",
                {
                    "attempt": attempt + 1,
                    "max_attempts": self.api_retries + 1,
                    "payload": _payload_debug_summary(working_payload),
                },
            )
            thinking_payload: dict[str, Any] = {
                "phase": "thinking",
                "status_text": "Calling model",
            }
            if isinstance(preflight_input_tokens, int):
                thinking_payload["input_tokens"] = preflight_input_tokens
            if isinstance(context_limit_tokens, int):
                thinking_payload["context_limit_tokens"] = context_limit_tokens
            await _emit_progress(progress_callback, thinking_payload)
            try:
                response = await client.responses.create(**working_payload)
                await _emit_trace(
                    trace_callback if self.trace_enabled else None,
                    "model_response",
                    {
                        "attempt": attempt + 1,
                        "summary": _summarize_response_for_trace(
                            _response_model_to_dict(response),
                            max_chars=self.trace_preview_max_chars,
                        ),
                    },
                )
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
                    await _emit_trace(
                        trace_callback if self.trace_enabled else None,
                        "model_retry_scheduled",
                        {
                            "attempt": attempt + 1,
                            "status_code": status_code,
                            "retry_delay_seconds": delay_s,
                            "reason": "rate_limited",
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
                                    "context_limit_tokens": context_limit_tokens,
                                },
                            )
                            await _emit_trace(
                                trace_callback if self.trace_enabled else None,
                                "tool_output_compacted",
                                {
                                    "attempt": attempt + 1,
                                    "max_chars": max_chars,
                                    "payload": _payload_debug_summary(reduced_payload),
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
                    await _emit_progress(
                        progress_callback,
                        {
                            "phase": "compacting",
                            "status_text": "Compacting context",
                            "detail_text": "Model context window exceeded",
                            "context_limit_tokens": context_limit_tokens,
                        },
                    )
                    compacted_id = await self._compact_previous_response(
                        previous_response_id=str(
                            working_payload["previous_response_id"]
                        ),
                        telemetry=telemetry,
                    )
                    if compacted_id:
                        await _emit_trace(
                            trace_callback if self.trace_enabled else None,
                            "context_compacted",
                            {
                                "from_response_id": working_payload[
                                    "previous_response_id"
                                ],
                                "compacted_response_id": compacted_id,
                            },
                        )
                        working_payload["previous_response_id"] = compacted_id
                        continue
                snippet = _extract_sdk_error_text(exc)[:500]
                payload_debug = _payload_debug_summary(working_payload)
                await _emit_trace(
                    trace_callback if self.trace_enabled else None,
                    "model_request_failed",
                    {
                        "attempt": attempt + 1,
                        "status_code": status_code,
                        "error_preview": _to_trace_preview(
                            snippet,
                            max_chars=self.trace_preview_max_chars,
                        ),
                        "payload": payload_debug,
                    },
                )
                raise RuntimeError(
                    f"Model API request failed ({status_code}): {snippet} "
                    f"| payload_debug={payload_debug}"
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
                    await _emit_trace(
                        trace_callback if self.trace_enabled else None,
                        "model_retry_scheduled",
                        {
                            "attempt": attempt + 1,
                            "retry_delay_seconds": delay_s,
                            "reason": type(exc).__name__,
                        },
                    )
                    await asyncio.sleep(delay_s)
                    continue
                payload_debug = _payload_debug_summary(working_payload)
                await _emit_trace(
                    trace_callback if self.trace_enabled else None,
                    "model_request_failed",
                    {
                        "attempt": attempt + 1,
                        "error_preview": _to_trace_preview(
                            str(exc),
                            max_chars=self.trace_preview_max_chars,
                        ),
                        "payload": payload_debug,
                    },
                )
                raise RuntimeError(
                    f"Model API request failed: {exc} | payload_debug={payload_debug}"
                ) from exc

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



def _build_turn_instructions(
    *,
    include_session_primer: bool,
    project_root: Path,
    selected_targets: list[str],
    skill_block: str,
    max_chars: int,
) -> str:
    chunks = [SYSTEM_PROMPT]
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
