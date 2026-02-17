"""Helper functions for agent orchestrator runtime and output shaping."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
from pathlib import Path
from typing import Any

from openai import APIStatusError

_RETRY_AFTER_TEXT_PATTERN = re.compile(
    r"Please try again in\s*(\d+(?:\.\d+)?)\s*(ms|s)\b",
    re.IGNORECASE,
)

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




def _normalize_skill_id(value: str) -> str:
    cleaned = value.strip().lower().replace("_", "-").replace(" ", "-")
    cleaned = re.sub(r"[^a-z0-9\-]+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "unknown-skill"


def _parse_fixed_skill_token_budgets(
    raw_value: str,
    *,
    default_skill_ids: list[str],
) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for raw_part in raw_value.split(","):
        part = raw_part.strip()
        if not part or ":" not in part:
            continue
        raw_skill_id, raw_budget = part.split(":", 1)
        skill_id = _normalize_skill_id(raw_skill_id)
        try:
            budget = int(raw_budget.strip())
        except ValueError:
            continue
        if budget <= 0:
            continue
        parsed[skill_id] = budget

    # Ensure every fixed skill gets at least a baseline budget.
    fallback = 10000
    for raw_skill_id in default_skill_ids:
        skill_id = _normalize_skill_id(raw_skill_id)
        parsed.setdefault(skill_id, fallback)
    return parsed


def _allocate_fixed_skill_char_caps(
    *,
    docs: list[Any],
    token_budgets: dict[str, int],
    chars_per_token: float,
    total_max_chars: int,
) -> dict[str, int]:
    def _doc_id(doc: Any) -> str:
        if isinstance(doc, dict):
            value = doc.get("id", "")
        else:
            value = getattr(doc, "id", "")
        return str(value or "")

    if not docs:
        return {}
    if total_max_chars <= 0:
        return {_doc_id(doc): 0 for doc in docs}

    requested_caps: dict[str, int] = {}
    for doc in docs:
        doc_id = _doc_id(doc)
        token_budget = max(0, int(token_budgets.get(doc_id, 0)))
        if token_budget <= 0:
            continue
        requested_caps[doc_id] = int(token_budget * chars_per_token)

    if not requested_caps:
        even_cap = max(1, total_max_chars // len(docs))
        return {_doc_id(doc): even_cap for doc in docs}

    fallback_cap = max(1, int(sum(requested_caps.values()) / len(requested_caps)))
    for doc in docs:
        doc_id = _doc_id(doc)
        requested_caps.setdefault(doc_id, fallback_cap)

    requested_total = sum(max(0, cap) for cap in requested_caps.values())
    if requested_total <= total_max_chars:
        return requested_caps

    scale = total_max_chars / requested_total
    allocated: dict[str, int] = {}
    remaining_chars = total_max_chars
    for index, doc in enumerate(docs):
        doc_id = _doc_id(doc)
        requested_cap = max(0, requested_caps.get(doc_id, 0))
        if index == len(docs) - 1:
            capped_value = remaining_chars
        else:
            scaled_cap = max(0, int(requested_cap * scale))
            capped_value = min(scaled_cap, remaining_chars)
        allocated[doc_id] = capped_value
        remaining_chars = max(0, remaining_chars - capped_value)

    return allocated


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
    raw_caps = skill_state.get("per_skill_max_chars", {})
    skill_caps = ""
    if isinstance(raw_caps, dict):
        pairs: list[tuple[str, int]] = []
        for raw_skill_id, raw_cap in raw_caps.items():
            if not isinstance(raw_skill_id, str):
                continue
            try:
                cap = int(raw_cap)
            except (TypeError, ValueError):
                continue
            pairs.append((_normalize_skill_id(raw_skill_id), cap))
        skill_caps = ",".join(f"{skill_id}:{cap}" for skill_id, cap in sorted(pairs))
    digest_input = f"{project_path}|{model}|{tool_names}|{skill_ids}|{skill_caps}"
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
        "project_create_path",
        "project_create_file",
        "project_create_folder",
        "project_move_path",
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


async def _emit_trace(
    callback: TraceCallback | None,
    event: str,
    payload: dict[str, Any],
) -> None:
    if callback is None:
        return
    maybe_awaitable = callback(event, payload)
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


def _to_trace_preview(value: Any, *, max_chars: int) -> Any:
    if isinstance(value, str):
        compact = value.strip()
        if len(compact) <= max_chars:
            return compact
        return f"{compact[: max_chars - 18]}...[trace-truncated]"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        serialized = str(value)
    if len(serialized) <= max_chars:
        return value
    return {
        "truncated": True,
        "preview": serialized[: max_chars - 18] + "...[trace-truncated]",
        "size_chars": len(serialized),
    }


def _summarize_function_call_for_trace(
    call: dict[str, Any],
    *,
    max_chars: int,
) -> dict[str, Any]:
    arguments_raw = call.get("arguments")
    parsed_arguments: dict[str, Any] | None = None
    if isinstance(arguments_raw, str):
        try:
            parsed = json.loads(arguments_raw)
            if isinstance(parsed, dict):
                parsed_arguments = parsed
        except Exception:
            parsed_arguments = None
    return {
        "id": call.get("id"),
        "call_id": call.get("call_id"),
        "name": call.get("name"),
        "arguments": (
            parsed_arguments
            if parsed_arguments is not None
            else _to_trace_preview(arguments_raw, max_chars=max_chars)
        ),
    }


def _summarize_tool_result_for_trace(
    value: dict[str, Any],
    *,
    max_chars: int,
) -> Any:
    summarized = _to_trace_preview(value, max_chars=max_chars)
    if isinstance(summarized, dict):
        return summarized
    if isinstance(value, dict):
        return value
    return {"preview": summarized}


def _summarize_response_for_trace(
    response: dict[str, Any],
    *,
    max_chars: int,
) -> dict[str, Any]:
    output = response.get("output")
    item_types: dict[str, int] = {}
    function_calls: list[dict[str, Any]] = []
    reasoning_previews: list[Any] = []
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                item_types["non_object"] = item_types.get("non_object", 0) + 1
                continue
            item_type = item.get("type")
            label = item_type if isinstance(item_type, str) and item_type else "object"
            item_types[label] = item_types.get(label, 0) + 1
            if item_type == "function_call":
                function_calls.append(
                    _summarize_function_call_for_trace(item, max_chars=max_chars)
                )
            elif item_type == "reasoning":
                reasoning_previews.append(
                    _to_trace_preview(item.get("summary"), max_chars=max_chars)
                )
    output_text = _extract_text(response)
    return {
        "id": response.get("id"),
        "output_items": len(output) if isinstance(output, list) else None,
        "output_item_types": item_types,
        "function_calls": function_calls,
        "reasoning_summaries": reasoning_previews[:8],
        "assistant_text_preview": _to_trace_preview(output_text, max_chars=max_chars),
    }
