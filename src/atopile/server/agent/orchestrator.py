"""Server-side agent orchestration with strict tool execution."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from atopile.dataclasses import AppContext
from atopile.model import builds as builds_domain
from atopile.server.agent import policy, tools
from atopile.server.domains import artifacts as artifacts_domain

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]
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
- Use datasheet_read when a component datasheet is needed; it attaches a PDF
  file for native model reading. Prefer lcsc_id to resolve via project graph.
- Use project_list_modules and project_module_children for quick structure
  discovery before deep file reads.
- If asked for design structure/architecture, call project_list_modules before
  answering and use project_module_children for any key entry points.
- If asked for BOM/parts list/procurement summary, call report_bom first (do
  not infer BOM from source files).
- If asked for parameters/constraints/computed values, call report_variables
  first (do not infer parameter values from source files).
- If asked to generate manufacturing outputs, call manufacturing_generate
  first, then track with build_logs_search, then inspect with
  manufacturing_summary.
- For build diagnostics, prefer build_logs_search with explicit log_levels/stage
  filters when logs are noisy.
- Use design_diagnostics when a build fails silently or diagnostics are needed.
- For significant multi-step tasks, use a short markdown checklist in your reply
  and mark completed items as you progress.
- End with a concise completion summary of what was done.
- Suggest one concrete next step and ask whether to continue.
- After editing, explain exactly which files changed.
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
        "- reports: for BOM/parts lists use report_bom; for computed parameters\n"
        "  and constraints use report_variables.\n"
        "- manufacturing: use manufacturing_generate to create artifacts, then\n"
        "  build_logs_search to track, then manufacturing_summary to inspect.\n"
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
        self._client: AsyncOpenAI | None = None

    async def run_turn(
        self,
        *,
        ctx: AppContext,
        project_root: str,
        history: list[dict[str, str]],
        user_message: str,
        selected_targets: list[str] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> AgentTurnResult:
        if not self.api_key:
            raise RuntimeError(
                "Missing API key. Set ATOPILE_AGENT_OPENAI_API_KEY or OPENAI_API_KEY."
            )

        project_path = tools.validate_tool_scope(project_root, ctx)
        include_session_primer = len(history) == 0
        context_text = await self._build_context(
            project_root=project_path,
            selected_targets=selected_targets or [],
        )

        request_input: list[dict[str, Any]] = [
            {"role": "system", "content": _SYSTEM_PROMPT}
        ]
        if include_session_primer:
            request_input.append(
                {
                    "role": "system",
                    "content": _build_session_primer(
                        project_root=project_path,
                        selected_targets=selected_targets or [],
                    ),
                }
            )
        request_input.extend(history)
        request_input.append(
            {
                "role": "user",
                "content": (
                    f"Project root: {project_path}\n"
                    f"Selected targets: {selected_targets or []}\n"
                    f"Context:\n{context_text}\n\n"
                    f"Request:\n{user_message}"
                ),
            }
        )

        tool_defs = tools.get_tool_definitions()
        await _emit_progress(
            progress_callback,
            {
                "phase": "thinking",
                "status_text": "Planning",
                "detail_text": "Reviewing request and project context",
            },
        )
        response = await self._responses_create(
            {
                "model": self.model,
                "input": request_input,
                "tools": tool_defs,
                "tool_choice": "auto",
            }
        )

        traces: list[ToolTrace] = []
        loops = 0
        while loops < self.max_tool_loops:
            loops += 1
            function_calls = _extract_function_calls(response)
            if not function_calls:
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
                return AgentTurnResult(text=text, tool_traces=traces, model=self.model)

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
                        result_payload=_sanitize_tool_output_for_model(result_payload),
                    )
                )

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
            response = await self._responses_create(
                {
                    "model": self.model,
                    "previous_response_id": response.get("id"),
                    "input": outputs,
                    "tools": tool_defs,
                    "tool_choice": "auto",
                }
            )

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
        lines.append(
            f"  - bom: {bom_targets if bom_targets else ['none']}"
        )
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

    async def _responses_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = self._get_client()
        for attempt in range(self.api_retries + 1):
            try:
                response = await client.responses.create(**payload)
                break
            except APIStatusError as exc:
                status_code = getattr(exc, "status_code", "unknown")
                should_retry = status_code == 429 and attempt < self.api_retries
                if should_retry:
                    delay_s = _compute_rate_limit_retry_delay_s(
                        exc=exc,
                        attempt=attempt,
                        base_delay_s=self.api_retry_base_delay_s,
                        max_delay_s=self.api_retry_max_delay_s,
                    )
                    await asyncio.sleep(delay_s)
                    continue
                snippet = _extract_sdk_error_text(exc)[:500]
                raise RuntimeError(
                    f"Model API request failed ({status_code}): {snippet}"
                ) from exc
            except (APIConnectionError, APITimeoutError) as exc:
                raise RuntimeError(f"Model API request failed: {exc}") from exc

        body = _response_model_to_dict(response)
        if not isinstance(body, dict):
            raise RuntimeError("Model API returned non-object response")
        return body

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
    backoff_delay_s = max(0.05, base_delay_s) * (2**max(0, attempt))
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
            f" lcsc_id={lcsc_id};"
            if isinstance(lcsc_id, str) and lcsc_id
            else ""
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
