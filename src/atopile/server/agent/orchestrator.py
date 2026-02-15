"""Server-side agent orchestration with strict tool execution."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from atopile.dataclasses import AppContext
from atopile.model import builds as builds_domain
from atopile.server.agent import policy, tools
from atopile.server.agent import skills as skills_domain
from atopile.server.domains import artifacts as artifacts_domain

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]
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
- Use package_ato_list/package_ato_search/package_ato_read to inspect installed
  package `.ato` sources under `.ato/modules` (and configured package reference
  roots) when authoring new designs.
- Use web_search for external/current web facts (vendor docs, standards, news,
  release changes) when project files do not contain the answer.
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
- For PCB layout automation, follow this sequence:
  (1) place critical connectors/components manually with
  layout_set_component_position, (2) review with
  autolayout_request_screenshot and iterate until placement is approved,
  (3) run autolayout_run for placement, (4) monitor with autolayout_status and
  only call autolayout_fetch_to_layout once state is awaiting_selection or
  completed, (5) review screenshots again, then (6) run autolayout_run for
  routing and repeat status->fetch->review.
- If asked to control ground pours/planes/stackup assumptions, call
  autolayout_configure_board_intent before running placement/routing.
- Use periodic check-ins for active autolayout jobs (autolayout_status with
  wait_seconds/poll_interval_seconds). If quality is not good enough, resume by
  calling autolayout_run with resume_board_id and another short (<=2 min) run.
- Treat autolayout_fetch_to_layout as apply-safe only when the job is ready.
  If it reports queued/running, wait the suggested seconds and check status
  again before retrying fetch/apply.
- Per-run autolayout timeout is capped at 2 minutes. Use iterative cycles:
  run short pass, review status/screenshots, then resume with resume_board_id if
  quality is not sufficient.
- For board preview images after placement/routing, use
  autolayout_request_screenshot and track the queued build with build_logs_search.
- For crowded boards, use autolayout_request_screenshot with
  highlight_components to spotlight selected parts while dimming the rest.
- For manual placement adjustments, use layout_get_component_position to query
  footprint xy/rotation by atopile address/reference, then
  layout_set_component_position for absolute or relative (nudge) transforms.
  Always read placement_check in the result to confirm on_board status and
  collision_count before continuing.
- Run layout_run_drc after major placement/routing changes to catch rule issues
  early (errors/warnings and top violation types).
- For build diagnostics, prefer build_logs_search with explicit log_levels/stage
  filters when logs are noisy.
- Use design_diagnostics when a build fails silently or diagnostics are needed.
- For significant multi-step tasks, use a short markdown checklist in your reply
  and mark completed items as you progress.
- End with a concise completion summary of what was done.
- Suggest one concrete next step and ask whether to continue.
- After editing, explain exactly which files changed.
- Avoid discovery-only loops: do not repeatedly call the same read/search tool
  with identical arguments. After gathering enough context, either execute the
  requested implementation (edits/builds/installs) or return a concise blocker.
- For atopile design authoring, default to abstraction-first structure:
  define functional modules (power, MCU, sensors, IO/debug) and connect them
  through high-level interfaces, instead of writing a monolithic manual netlist.
- Prefer interface-driven wiring (`ElectricPower`, `I2C`, `SPI`, `UART`, `SWD`,
  `ElectricLogic`, etc.) and bridge/connect modules at top-level.
- Use generic passives by default (`Resistor`, `Capacitor`, `Inductor`) with
  parameter constraints (value/tolerance/voltage/package/tempco). Do not select
  fixed vendor passives unless explicitly requested or manufacturing constraints
  require a specific MPN.
- Use explicit package parts for ICs/connectors/protection/mechanics where
  needed, but keep passives abstract and constrained whenever possible.
- Prefer arrays/loops/templates for repeated decoupling and pull-up patterns.
- Avoid hand-wiring every pin at top-level unless no interface abstraction is
  available for that subcircuit.
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
        self.skills_dir = Path(
            os.getenv(
                "ATOPILE_AGENT_SKILLS_DIR",
                "/Users/narayanpowderly/projects/atopile/.claude/skills",
            )
        ).expanduser()
        raw_skill_mode = os.getenv("ATOPILE_AGENT_SKILL_MODE", "fixed").strip().lower()
        if raw_skill_mode not in {"fixed", "dynamic"}:
            raw_skill_mode = "dynamic"
        self.skill_mode = raw_skill_mode
        raw_fixed_skill_ids = os.getenv("ATOPILE_AGENT_FIXED_SKILL_IDS", "agent,ato")
        self.fixed_skill_ids = [
            part.strip() for part in raw_fixed_skill_ids.split(",") if part.strip()
        ] or ["agent", "ato"]
        self.fixed_skill_total_max_chars = int(
            os.getenv("ATOPILE_AGENT_FIXED_SKILL_TOTAL_MAX_CHARS", "220000")
        )
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
        prefix_default_max_chars = "220000" if self.skill_mode == "fixed" else "18000"
        self.prefix_max_chars = int(
            os.getenv("ATOPILE_AGENT_PREFIX_MAX_CHARS", prefix_default_max_chars)
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

        if self.skill_mode == "fixed":
            fixed_docs, missing_skill_ids = skills_domain.load_fixed_skill_docs(
                skills_dir=self.skills_dir,
                skill_ids=self.fixed_skill_ids,
                ttl_s=self.skill_index_ttl_s,
            )
            if fixed_docs:
                skill_block = skills_domain.render_fixed_skills_block(
                    docs=fixed_docs,
                    max_chars=self.fixed_skill_total_max_chars,
                )
                skill_state = skills_domain.build_fixed_skill_state(
                    skills_dir=self.skills_dir,
                    requested_skill_ids=self.fixed_skill_ids,
                    selected_docs=fixed_docs,
                    missing_skill_ids=missing_skill_ids,
                    rendered_total_chars=len(skill_block),
                    max_chars=self.fixed_skill_total_max_chars,
                )
            else:
                # Safety fallback: keep runtime functional even before fixed
                # skill files are fully migrated.
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
        else:
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

        tool_defs = tools.get_tool_definitions()
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
        recent_tool_signatures: list[str] = []
        loop_guard_hits = 0
        consecutive_tool_failures = 0
        no_progress_loops = 0
        started_at_s = time.monotonic()
        while loops < self.max_tool_loops:
            elapsed_s = time.monotonic() - started_at_s
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
            loop_traces: list[ToolTrace] = []
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
            await _emit_progress(
                progress_callback,
                {
                    "phase": "thinking",
                    "status_text": "Calling model",
                    "detail_text": f"Attempt {attempt + 1}/{self.api_retries + 1}",
                },
            )
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
                payload_debug = _payload_debug_summary(working_payload)
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
                    await asyncio.sleep(delay_s)
                    continue
                payload_debug = _payload_debug_summary(working_payload)
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


def _build_execution_guard_inputs_for_model(message: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": (
                "Execution guard from runtime: avoid repetitive discovery-only "
                "loops.\n"
                f"{message}\n"
                "Your next step must be either:\n"
                "- execute a concrete implementation tool call, or\n"
                "- return a concise blocker with the exact missing input."
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


def trim_single_line(value: str, max_chars: int) -> str:
    compact = " ".join(value.split()).strip()
    if len(compact) <= max_chars:
        return compact
    if max_chars <= 0:
        return ""
    if max_chars == 1:
        return compact[:1]
    return f"{compact[: max_chars - 1]}..."


def _tool_call_signature(*, tool_name: str, args: dict[str, Any]) -> str:
    try:
        serialized = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        serialized = str(args)
    return f"{tool_name}:{serialized[:400]}"


def _worker_discovery_tool_names() -> set[str]:
    return {
        "project_read_file",
        "project_list_files",
        "project_search",
        "project_list_modules",
        "project_module_children",
        "stdlib_list",
        "stdlib_get_item",
        "examples_list",
        "examples_search",
        "examples_read_ato",
        "package_ato_list",
        "package_ato_search",
        "package_ato_read",
        "web_search",
        "parts_search",
        "packages_search",
        "build_logs_search",
        "design_diagnostics",
        "report_bom",
        "report_variables",
        "manufacturing_summary",
        "autolayout_status",
        "datasheet_read",
        "layout_get_component_position",
        "layout_run_drc",
    }


def _worker_execution_tool_names() -> set[str]:
    return {
        "project_edit_file",
        "project_write_file",
        "project_replace_text",
        "project_rename_path",
        "project_delete_path",
        "parts_install",
        "packages_install",
        "build_run",
        "manufacturing_generate",
        "autolayout_run",
        "autolayout_fetch_to_layout",
        "autolayout_request_screenshot",
        "autolayout_configure_board_intent",
        "layout_set_component_position",
        "layout_run_drc",
    }


def _build_worker_loop_guard_message(
    *,
    traces: list[ToolTrace],
    recent_tool_signatures: list[str],
    loops: int,
    guard_hits: int,
    window: int,
    min_discovery: int,
) -> str | None:
    if loops < 3 or len(traces) < min_discovery:
        return None

    discovery_tools = _worker_discovery_tool_names()
    execution_tools = _worker_execution_tool_names()

    recent_traces = traces[-window:]
    recent_signatures = recent_tool_signatures[-window:]
    if not recent_traces or not recent_signatures:
        return None

    execution_count = sum(1 for trace in recent_traces if trace.name in execution_tools)
    if execution_count > 0:
        return None

    discovery_count = sum(1 for trace in recent_traces if trace.name in discovery_tools)
    if discovery_count < min_discovery:
        return None

    repeated_tail = (
        len(recent_signatures) >= 3 and len(set(recent_signatures[-3:])) == 1
    )
    signature_uniqueness = len(set(recent_signatures)) / max(1, len(recent_signatures))
    low_uniqueness = signature_uniqueness <= 0.55
    if not repeated_tail and not low_uniqueness:
        return None

    if guard_hits >= 2:
        return (
            "You are still repeating discovery calls without concrete implementation "
            "progress. Stop discovery churn now."
        )

    last_tool = recent_traces[-1].name
    return (
        "Recent tool activity is discovery-heavy and repetitive"
        f" (latest tool: {last_tool}). "
        "Do not repeat identical read/search calls."
    )


def _build_worker_loop_guard_stop_text(
    *,
    traces: list[ToolTrace],
    loops: int,
) -> str:
    recent_names = [trace.name for trace in traces[-6:]]
    recent_text = ", ".join(recent_names) if recent_names else "none"
    return (
        "Stopped to prevent a repetitive discovery loop after "
        f"{len(traces)} tool calls across {loops} loops. "
        "I need to switch to concrete execution (edits/builds/installs) or report a "
        "specific blocker. "
        f"Recent tools: {recent_text}."
    )


def _loop_has_concrete_progress(loop_traces: list[ToolTrace]) -> bool:
    if not loop_traces:
        return False

    execution_tools = _worker_execution_tool_names()
    for trace in loop_traces:
        if not trace.ok:
            continue

        if trace.name == "autolayout_fetch_to_layout":
            if bool(trace.result.get("applied", False)):
                return True
            if isinstance(trace.result.get("applied_layout_path"), str):
                return True
            continue

        if trace.name == "autolayout_status":
            state = str(trace.result.get("state", "")).lower()
            candidates = trace.result.get("candidate_count")
            if state in {"awaiting_selection", "completed"} and isinstance(
                candidates, int
            ):
                return candidates > 0
            continue

        if trace.name in execution_tools:
            return True

    return False


def _build_worker_failure_streak_stop_text(
    *,
    traces: list[ToolTrace],
    loops: int,
    failure_streak: int,
) -> str:
    failing = [trace for trace in traces[-8:] if not trace.ok]
    details: list[str] = []
    for trace in failing[-3:]:
        error = trace.result.get("error")
        if isinstance(error, str) and error.strip():
            details.append(f"{trace.name}: {trim_single_line(error, 110)}")
        else:
            details.append(trace.name)
    detail_text = "; ".join(details) if details else "no error details captured"
    return (
        "Stopped after repeated tool failures to avoid stalling "
        f"({failure_streak} consecutive failures across {loops} loops). "
        "Need a corrected next step or missing input before continuing. "
        f"Recent failures: {detail_text}."
    )


def _build_worker_no_progress_stop_text(
    *,
    traces: list[ToolTrace],
    loops: int,
    no_progress_loops: int,
) -> str:
    recent_names = [trace.name for trace in traces[-8:]]
    recent_text = ", ".join(recent_names) if recent_names else "none"
    return (
        "Stopped after repeated loops without concrete progress "
        f"({no_progress_loops} loops, {len(traces)} tool calls). "
        "Need to change strategy (implement edit/build/apply) or report a blocker. "
        f"Recent tools: {recent_text}. "
        "If monitoring a background job, use a longer wait_seconds before the next "
        "status check."
    )


def _build_worker_time_budget_stop_text(
    *,
    traces: list[ToolTrace],
    loops: int,
    elapsed_seconds: float,
) -> str:
    recent_names = [trace.name for trace in traces[-6:]]
    recent_text = ", ".join(recent_names) if recent_names else "none"
    return (
        "Stopped after exceeding the per-turn time budget to avoid stalling "
        f"({elapsed_seconds:.1f}s, {loops} loops, {len(traces)} tool calls). "
        f"Recent tools: {recent_text}."
    )


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


def _payload_debug_summary(payload: dict[str, Any]) -> dict[str, Any]:
    raw_input = payload.get("input")
    item_types: dict[str, int] = {}
    function_output_call_ids: list[str] = []
    if isinstance(raw_input, list):
        for item in raw_input:
            label = _payload_input_item_label(item)
            item_types[label] = item_types.get(label, 0) + 1
            if isinstance(item, dict) and item.get("type") == "function_call_output":
                call_id = item.get("call_id")
                if isinstance(call_id, str) and call_id:
                    function_output_call_ids.append(call_id)

    previous_response_id = payload.get("previous_response_id")
    return {
        "previous_response_id": (
            previous_response_id
            if isinstance(previous_response_id, str) and previous_response_id
            else None
        ),
        "input_items": len(raw_input) if isinstance(raw_input, list) else None,
        "input_item_types": item_types,
        "function_call_output_count": len(function_output_call_ids),
        "function_call_output_call_ids": function_output_call_ids[:12],
    }


def _payload_input_item_label(item: Any) -> str:
    if not isinstance(item, dict):
        return "non_object"
    item_type = item.get("type")
    if isinstance(item_type, str) and item_type:
        return item_type
    role = item.get("role")
    if isinstance(role, str) and role:
        return f"role:{role}"
    return "object"


# Colocated tests moved from `test/server/agent/test_orchestrator_output.py`.
try:
    import pytest
except Exception:  # pragma: no cover - runtime deployments may omit pytest
    pytest = None

if pytest is not None:
    import asyncio
    import json
    from pathlib import Path

    import httpx
    from openai import APIStatusError

    from atopile.dataclasses import AppContext
    from atopile.server.agent.orchestrator import (
        _SYSTEM_PROMPT,
        AgentOrchestrator,
        ToolTrace,
        _build_function_call_outputs_for_model,
        _build_prompt_cache_key,
        _build_session_primer,
        _build_worker_loop_guard_message,
        _extract_retry_after_delay_s,
        _sanitize_tool_output_for_model,
        _tool_call_signature,
        _trim_user_message,
    )

    def _test_sanitize_tool_output_removes_internal_keys() -> None:
        payload = {
            "path": "main.ato",
            "diff": {"added_lines": 2, "removed_lines": 1},
            "_ui": {
                "edit_diff": {
                    "before_content": "a\n",
                    "after_content": "b\n",
                }
            },
            "nested": {
                "_private": "drop",
                "value": 1,
                "items": [{"ok": True, "_debug": "drop-me"}],
            },
        }

        sanitized = _sanitize_tool_output_for_model(payload)

        assert "_ui" not in sanitized
        assert sanitized["path"] == "main.ato"
        assert sanitized["diff"]["added_lines"] == 2
        assert "_private" not in sanitized["nested"]
        assert sanitized["nested"]["items"][0] == {"ok": True}

    def _test_build_function_call_outputs_attaches_datasheet_file() -> None:
        outputs = _build_function_call_outputs_for_model(
            call_id="call_123",
            tool_name="datasheet_read",
            result_payload={
                "found": True,
                "openai_file_id": "file-abc123",
                "source": "https://example.com/ds.pdf",
                "filename": "ds.pdf",
                "query": "boot0 and reset",
            },
        )

        assert len(outputs) == 2
        assert outputs[0]["type"] == "function_call_output"
        assert outputs[0]["call_id"] == "call_123"
        assert outputs[1]["role"] == "user"
        assert outputs[1]["content"][1] == {
            "type": "input_file",
            "file_id": "file-abc123",
        }

    def _test_build_function_call_outputs_nudges_after_parts_install() -> None:
        outputs = _build_function_call_outputs_for_model(
            call_id="call_456",
            tool_name="parts_install",
            result_payload={
                "success": True,
                "lcsc_id": "C521608",
                "identifier": "STM32G474RET6",
            },
        )

        assert len(outputs) == 2
        assert outputs[0]["type"] == "function_call_output"
        assert outputs[0]["call_id"] == "call_456"
        assert outputs[1]["role"] == "user"
        text = outputs[1]["content"][0]["text"]
        assert "parts_install completed" in text
        assert "datasheet_read next" in text

    def _make_api_status_error(
        *,
        status_code: int,
        body: dict | None = None,
        headers: dict[str, str] | None = None,
        text: str | None = None,
    ) -> APIStatusError:
        request = httpx.Request("POST", "https://api.openai.com/v1/responses")
        response = httpx.Response(
            status_code=status_code,
            request=request,
            headers=headers,
            text=text if text is not None else (json.dumps(body) if body else ""),
        )
        return APIStatusError(
            "api status error",
            response=response,
            body=body,
        )

    def _test_extract_retry_after_delay_from_message_text() -> None:
        exc = _make_api_status_error(
            status_code=429,
            body={
                "error": {
                    "message": (
                        "Rate limit reached. Please try again in 578ms. "
                        "Visit dashboard."
                    ),
                    "code": "rate_limit_exceeded",
                }
            },
        )
        delay_s = _extract_retry_after_delay_s(exc)
        assert delay_s is not None
        assert delay_s == 0.578

    def _test_responses_create_retries_on_429(monkeypatch) -> None:
        orchestrator = AgentOrchestrator()
        sleep_calls: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        monkeypatch.setattr(
            "atopile.server.agent.orchestrator.asyncio.sleep", fake_sleep
        )

        class StubResponses:
            def __init__(self) -> None:
                self.calls = 0

            async def create(self, **_: object) -> dict:
                self.calls += 1
                if self.calls == 1:
                    raise _make_api_status_error(
                        status_code=429,
                        body={
                            "error": {
                                "message": "Please try again in 250ms.",
                                "code": "rate_limit_exceeded",
                            }
                        },
                        headers={"retry-after-ms": "250"},
                    )
                return {"id": "resp_ok", "output": [], "output_text": "ok"}

        class StubClient:
            def __init__(self) -> None:
                self.responses = StubResponses()

        stub_client = StubClient()
        orchestrator._client = stub_client  # type: ignore[assignment]

        result = asyncio.run(
            orchestrator._responses_create({"model": "gpt-5-codex", "input": "ping"})
        )
        assert result["id"] == "resp_ok"
        assert stub_client.responses.calls == 2
        assert sleep_calls == [0.25]

    def _test_responses_create_compacts_and_retries_on_context_overflow() -> None:
        orchestrator = AgentOrchestrator()
        telemetry: dict[str, object] = {"api_retry_count": 0, "compaction_events": []}

        class StubResponses:
            def __init__(self) -> None:
                self.calls = 0
                self.last_previous_response_id: str | None = None
                self.compact_calls = 0

            async def create(self, **kwargs: object) -> dict:
                self.calls += 1
                self.last_previous_response_id = str(kwargs.get("previous_response_id"))
                if self.calls == 1:
                    raise _make_api_status_error(
                        status_code=400,
                        body={
                            "error": {
                                "message": "input exceeds context window",
                                "code": "context_length_exceeded",
                            }
                        },
                    )
                return {"id": "resp_ok", "output": [], "output_text": "ok"}

            async def compact(self, **_: object) -> dict:
                self.compact_calls += 1
                return {"id": "resp_compact", "output": []}

        class StubClient:
            def __init__(self) -> None:
                self.responses = StubResponses()

        stub_client = StubClient()
        orchestrator._client = stub_client  # type: ignore[assignment]
        result = asyncio.run(
            orchestrator._responses_create(
                {
                    "model": "gpt-5-codex",
                    "previous_response_id": "resp_old",
                    "input": [{"role": "user", "content": "hello"}],
                },
                telemetry=telemetry,
            )
        )

        assert result["id"] == "resp_ok"
        assert stub_client.responses.calls == 2
        assert stub_client.responses.compact_calls == 1
        assert stub_client.responses.last_previous_response_id == "resp_compact"
        events = telemetry.get("compaction_events")
        assert isinstance(events, list)
        assert len(events) == 1

    def _test_prompt_cache_key_is_stable_for_same_inputs() -> None:
        key_a = _build_prompt_cache_key(
            project_path=Path("/tmp/demo"),
            tool_defs=[{"name": "project_read_file"}, {"name": "build_run"}],
            skill_state={"selected_skill_ids": ["dev", "domain-layer"]},
            model="gpt-5-codex",
        )
        key_b = _build_prompt_cache_key(
            project_path=Path("/tmp/demo"),
            tool_defs=[{"name": "build_run"}, {"name": "project_read_file"}],
            skill_state={"selected_skill_ids": ["dev", "domain-layer"]},
            model="gpt-5-codex",
        )
        assert key_a == key_b
        assert key_a.startswith("atopile-agent:")

    def _test_trim_user_message_preserves_head_and_tail() -> None:
        message = "A" * 120 + "B" * 120
        trimmed = _trim_user_message(message, max_chars=120)
        assert len(trimmed) <= 150
        assert "truncated" in trimmed.lower()
        assert trimmed.startswith("A")
        assert trimmed.endswith("B")

    def _test_build_worker_loop_guard_message_detects_repetitive_discovery() -> None:
        traces = [
            ToolTrace(
                name="project_read_file",
                args={"path": "main.ato"},
                ok=True,
                result={"path": "main.ato"},
            )
            for _ in range(6)
        ]
        signatures = [
            _tool_call_signature(
                tool_name="project_read_file", args={"path": "main.ato"}
            )
            for _ in range(6)
        ]

        message = _build_worker_loop_guard_message(
            traces=traces,
            recent_tool_signatures=signatures,
            loops=6,
            guard_hits=0,
            window=8,
            min_discovery=6,
        )

        assert message is not None
        assert "repetitive" in message.lower()

    def _test_build_worker_loop_guard_message_ignores_execution_progress() -> None:
        traces = [
            ToolTrace(
                name="project_read_file",
                args={"path": "main.ato"},
                ok=True,
                result={"path": "main.ato"},
            )
            for _ in range(5)
        ] + [
            ToolTrace(
                name="project_edit_file",
                args={"path": "main.ato"},
                ok=True,
                result={"operations_applied": 1},
            )
        ]
        signatures = [
            _tool_call_signature(tool_name=trace.name, args=trace.args)
            for trace in traces
        ]

        message = _build_worker_loop_guard_message(
            traces=traces,
            recent_tool_signatures=signatures,
            loops=6,
            guard_hits=0,
            window=8,
            min_discovery=6,
        )

        assert message is None

    def _test_run_worker_turn_stops_repetitive_discovery_loop(
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")
        (tmp_path / "main.ato").write_text("module App:\n    pass\n", encoding="utf-8")

        orchestrator = AgentOrchestrator()
        orchestrator.worker_loop_guard_min_discovery = 4
        orchestrator.worker_loop_guard_max_hits = 1
        orchestrator.max_tool_loops = 30

        async def fake_build_context(**_: object) -> str:
            return "Project summary: minimal test context"

        call_counter = {"count": 0}

        async def fake_create_with_context_control(**_: object) -> dict[str, object]:
            call_counter["count"] += 1
            return {
                "id": f"resp_{call_counter['count']}",
                "output": [
                    {
                        "type": "function_call",
                        "id": f"fc_{call_counter['count']}",
                        "call_id": f"call_{call_counter['count']}",
                        "name": "project_read_file",
                        "arguments": json.dumps(
                            {"path": "main.ato", "start_line": 1, "max_lines": 40}
                        ),
                    }
                ],
            }

        async def fake_execute_tool(**_: object) -> dict[str, object]:
            return {"path": "main.ato", "content": "1:aaaa|module App:"}

        monkeypatch.setattr(orchestrator, "_build_context", fake_build_context)
        monkeypatch.setattr(
            orchestrator,
            "_responses_create_with_context_control",
            fake_create_with_context_control,
        )
        monkeypatch.setattr(
            "atopile.server.agent.orchestrator.tools.execute_tool",
            fake_execute_tool,
        )

        result = asyncio.run(
            orchestrator.run_turn(
                ctx=AppContext(workspace_paths=[tmp_path]),
                project_root=str(tmp_path),
                history=[],
                user_message="Implement the requested feature.",
                selected_targets=["default"],
            )
        )

        assert "repetitive discovery loop" in result.text.lower()
        assert len(result.tool_traces) >= 4
        assert call_counter["count"] >= 4

    def _test_run_worker_turn_stops_on_repeated_tool_failures(
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")
        (tmp_path / "main.ato").write_text("module App:\n    pass\n", encoding="utf-8")

        orchestrator = AgentOrchestrator()
        orchestrator.worker_failure_streak_limit = 2
        orchestrator.max_tool_loops = 20

        async def fake_build_context(**_: object) -> str:
            return "Project summary: minimal test context"

        call_counter = {"count": 0}

        async def fake_create_with_context_control(**_: object) -> dict[str, object]:
            call_counter["count"] += 1
            return {
                "id": f"resp_{call_counter['count']}",
                "output": [
                    {
                        "type": "function_call",
                        "id": f"fc_{call_counter['count']}",
                        "call_id": f"call_{call_counter['count']}",
                        "name": "project_edit_file",
                        "arguments": json.dumps(
                            {
                                "path": "main.ato",
                                "edits": [
                                    {
                                        "op": "replace",
                                        "line": "1:aaaa",
                                        "old": "module App:",
                                        "new": "module App:",
                                    }
                                ],
                            }
                        ),
                    }
                ],
            }

        async def fake_execute_tool(**_: object) -> dict[str, object]:
            raise RuntimeError("hash anchor mismatch")

        monkeypatch.setattr(orchestrator, "_build_context", fake_build_context)
        monkeypatch.setattr(
            orchestrator,
            "_responses_create_with_context_control",
            fake_create_with_context_control,
        )
        monkeypatch.setattr(
            "atopile.server.agent.orchestrator.tools.execute_tool",
            fake_execute_tool,
        )

        result = asyncio.run(
            orchestrator.run_turn(
                ctx=AppContext(workspace_paths=[tmp_path]),
                project_root=str(tmp_path),
                history=[],
                user_message="Apply edit.",
                selected_targets=["default"],
            )
        )

        assert "repeated tool failures" in result.text.lower()
        assert len(result.tool_traces) >= 2

    def _test_run_worker_turn_stops_after_no_concrete_progress(
        monkeypatch,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

        orchestrator = AgentOrchestrator()
        orchestrator.worker_no_progress_loop_limit = 3
        orchestrator.worker_loop_guard_min_discovery = 10
        orchestrator.max_tool_loops = 30

        async def fake_build_context(**_: object) -> str:
            return "Project summary: minimal test context"

        call_counter = {"count": 0}

        async def fake_create_with_context_control(**_: object) -> dict[str, object]:
            call_counter["count"] += 1
            return {
                "id": f"resp_{call_counter['count']}",
                "output": [
                    {
                        "type": "function_call",
                        "id": f"fc_{call_counter['count']}",
                        "call_id": f"call_{call_counter['count']}",
                        "name": "autolayout_status",
                        "arguments": json.dumps({"job_id": "al-123456789abc"}),
                    }
                ],
            }

        async def fake_execute_tool(**_: object) -> dict[str, object]:
            return {
                "job_id": "al-123456789abc",
                "state": "running",
                "candidate_count": 0,
            }

        monkeypatch.setattr(orchestrator, "_build_context", fake_build_context)
        monkeypatch.setattr(
            orchestrator,
            "_responses_create_with_context_control",
            fake_create_with_context_control,
        )
        monkeypatch.setattr(
            "atopile.server.agent.orchestrator.tools.execute_tool",
            fake_execute_tool,
        )

        result = asyncio.run(
            orchestrator.run_turn(
                ctx=AppContext(workspace_paths=[tmp_path]),
                project_root=str(tmp_path),
                history=[],
                user_message="Keep monitoring this job.",
                selected_targets=["default"],
            )
        )

        assert "without concrete progress" in result.text.lower()
        assert len(result.tool_traces) >= 3

    class TestOrchestratorOutput:
        test_sanitize_tool_output_removes_internal_keys = staticmethod(
            _test_sanitize_tool_output_removes_internal_keys
        )
        test_build_function_call_outputs_attaches_datasheet_file = staticmethod(
            _test_build_function_call_outputs_attaches_datasheet_file
        )
        test_build_function_call_outputs_nudges_after_parts_install = staticmethod(
            _test_build_function_call_outputs_nudges_after_parts_install
        )
        test_extract_retry_after_delay_from_message_text = staticmethod(
            _test_extract_retry_after_delay_from_message_text
        )
        test_responses_create_retries_on_429 = staticmethod(
            _test_responses_create_retries_on_429
        )
        test_responses_create_compacts_and_retries_on_context_overflow = staticmethod(
            _test_responses_create_compacts_and_retries_on_context_overflow
        )
        test_prompt_cache_key_is_stable_for_same_inputs = staticmethod(
            _test_prompt_cache_key_is_stable_for_same_inputs
        )
        test_trim_user_message_preserves_head_and_tail = staticmethod(
            _test_trim_user_message_preserves_head_and_tail
        )
        test_build_worker_loop_guard_message_detects_repetitive_discovery = (
            staticmethod(
                _test_build_worker_loop_guard_message_detects_repetitive_discovery
            )
        )
        test_build_worker_loop_guard_message_ignores_execution_progress = staticmethod(
            _test_build_worker_loop_guard_message_ignores_execution_progress
        )
        test_run_worker_turn_stops_repetitive_discovery_loop = staticmethod(
            _test_run_worker_turn_stops_repetitive_discovery_loop
        )
        test_run_worker_turn_stops_on_repeated_tool_failures = staticmethod(
            _test_run_worker_turn_stops_on_repeated_tool_failures
        )
        test_run_worker_turn_stops_after_no_concrete_progress = staticmethod(
            _test_run_worker_turn_stops_after_no_concrete_progress
        )
