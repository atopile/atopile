"""Inference and summarization helpers for the agent mediator."""

from __future__ import annotations

from typing import Any

_STALE_PREFIXES: list[tuple[str, float]] = [
    ("build", 90.0),
    ("design_", 90.0),
    ("autolayout_", 75.0),
    ("layout_", 120.0),
    ("project_", 300.0),
]


def _stale_after_seconds(tool_name: str) -> float:
    for prefix, seconds in _STALE_PREFIXES:
        if tool_name.startswith(prefix):
            return seconds
    return 600.0


def _extract_context_id(result: dict[str, Any]) -> str | None:
    nested_job = result.get("job")
    if isinstance(nested_job, dict):
        nested_job_id = nested_job.get("job_id")
        if isinstance(nested_job_id, str) and nested_job_id:
            return nested_job_id

    for key in (
        "job_id",
        "latest_job_id",
        "resolved_job_id",
        "build_id",
        "provider_job_ref",
        "item_id",
        "path",
        "identifier",
    ):
        value = result.get(key)
        if isinstance(value, str) and value:
            return value

    jobs = result.get("jobs")
    if isinstance(jobs, list):
        for job in jobs:
            if not isinstance(job, dict):
                continue
            candidate_id = job.get("job_id")
            if isinstance(candidate_id, str) and candidate_id:
                return candidate_id

    return None


def _trim(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _str(result: dict[str, Any], key: str) -> str | None:
    """Return result[key] if it's a non-empty string, else None."""
    v = result.get(key)
    return v if isinstance(v, str) and v else None


def _int(result: dict[str, Any], key: str) -> int | None:
    """Return result[key] if it's an int, else None."""
    v = result.get(key)
    return v if isinstance(v, int) else None


# --- per-tool summarizers (registered in _SUMMARIZERS below) ---


def _summarize_create(result: dict[str, Any]) -> str:
    path = _str(result, "path")
    kind = _str(result, "kind")
    if path and kind:
        return f"created {kind}: {path}"
    if path:
        return f"created: {path}"
    return "path created"


def _summarize_rename(result: dict[str, Any]) -> str:
    old, new = _str(result, "old_path"), _str(result, "new_path")
    if old and new:
        return f"renamed {old} -> {new}"
    return "path renamed"


def _summarize_delete(result: dict[str, Any]) -> str:
    path = _str(result, "path")
    return f"deleted: {path}" if path else "path deleted"


def _summarize_build_run(result: dict[str, Any]) -> str:
    targets = result.get("build_targets")
    if isinstance(targets, list):
        return f"{len(targets)} build(s) queued"
    return "ok"


def _summarize_autolayout_run(result: dict[str, Any]) -> str:
    state = _str(result, "state")
    return f"autolayout {state}" if state else "autolayout job queued"


def _summarize_autolayout_status(result: dict[str, Any]) -> str:
    state = _str(result, "state")
    candidates = _int(result, "candidate_count")
    if state:
        if candidates is not None:
            return f"state={state}; candidates={candidates}"
        return f"state={state}"
    latest = _str(result, "latest_job_id")
    total = _int(result, "total_jobs")
    if latest:
        return (
            f"latest job={latest}; total={total}"
            if total is not None
            else f"latest job={latest}"
        )
    return "ok"


def _summarize_autolayout_fetch(result: dict[str, Any]) -> str:
    candidate = _str(result, "selected_candidate_id")
    if candidate:
        return f"applied {candidate}"
    if result.get("ready_to_apply") is False:
        state = _str(result, "state")
        if state:
            return f"waiting ({state})"
    return "layout candidate applied"


def _summarize_screenshot(result: dict[str, Any]) -> str:
    view = _str(result, "view")
    return f"{view} screenshot rendered" if view else "screenshot rendered"


def _summarize_drc(result: dict[str, Any]) -> str:
    errors, total = _int(result, "error_count"), _int(result, "total_findings")
    if errors is not None and total is not None:
        return f"drc: {errors} error(s), {total} finding(s)"
    return "drc report generated"


def _summarize_board_intent(result: dict[str, Any]) -> str:
    target = _str(result, "build_target")
    return f"board intent updated for {target}" if target else "board intent updated"


def _summarize_web_search(result: dict[str, Any]) -> str:
    count = _int(result, "returned_results")
    query = _str(result, "query")
    if count is not None:
        if query:
            return f"{count} web results for '{_trim(query.strip(), 30)}'"
        return f"{count} web results"
    return "web search complete"


def _summarize_get_position(result: dict[str, Any]) -> str:
    if bool(result.get("found", False)):
        comp = result.get("component")
        if isinstance(comp, dict):
            ref = _str(comp, "reference")
            if ref:
                return f"position for {ref}"
        return "component position fetched"
    suggestions = result.get("suggestions")
    if isinstance(suggestions, list):
        return f"not found; {len(suggestions)} suggestion(s)"
    return "component not found"


def _summarize_set_position(result: dict[str, Any]) -> str:
    if bool(result.get("updated", False)):
        after = result.get("after")
        if isinstance(after, dict):
            ref = _str(after, "reference")
            if ref:
                return f"moved {ref}"
        return "component placement updated"
    suggestions = result.get("suggestions")
    if isinstance(suggestions, list):
        return f"not found; {len(suggestions)} suggestion(s)"
    return "component placement not updated"


_SUMMARIZERS: dict[str, object] = {
    "project_create_path": _summarize_create,
    "project_create_file": _summarize_create,
    "project_create_folder": _summarize_create,
    "project_rename_path": _summarize_rename,
    "project_move_path": _summarize_rename,
    "project_delete_path": _summarize_delete,
    "build_run": _summarize_build_run,
    "autolayout_run": _summarize_autolayout_run,
    "autolayout_status": _summarize_autolayout_status,
    "autolayout_fetch_to_layout": _summarize_autolayout_fetch,
    "autolayout_request_screenshot": _summarize_screenshot,
    "layout_run_drc": _summarize_drc,
    "autolayout_configure_board_intent": _summarize_board_intent,
    "web_search": _summarize_web_search,
    "layout_get_component_position": _summarize_get_position,
    "layout_set_component_position": _summarize_set_position,
}


def _summarize_result(name: str, ok: bool, result: dict[str, Any]) -> str:
    if not ok:
        error = _str(result, "error")
        return _trim(error, 120) if error else "failed"

    message = _str(result, "message")
    if message:
        return _trim(message, 120)

    total = _int(result, "total")
    if total is not None:
        return f"{total} items"

    ops = _int(result, "operations_applied")
    if ops is not None:
        return f"{ops} edits applied"

    summarizer = _SUMMARIZERS.get(name)
    if summarizer is not None:
        return summarizer(result)  # type: ignore[operator]

    return "ok"


def _maybe_explain_failure_suggestion(
    *,
    message: str,
    memory_view: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    text = message.strip().lower()
    triggers = (
        "explain failure",
        "why did it fail",
        "diagnose",
        "debug build",
        "lint current design",
    )
    if not any(phrase in text for phrase in triggers) and text:
        return None

    build_context = None
    build_logs_entry = memory_view.get("build_logs_search")
    if build_logs_entry:
        context_id = build_logs_entry.get("context_id")
        if isinstance(context_id, str) and context_id:
            build_context = context_id

    prompt = "Run `design_diagnostics`, then summarize likely root cause."
    if build_context:
        prompt += (
            f" Use `build_logs_search` with build_id='{build_context}' for details."
        )

    return {
        "name": "explain_failure",
        "category": "diagnostics",
        "score": 4.2,
        "reason": "Composite failure triage workflow.",
        "tooltip": "Runs diagnostics-first failure analysis before suggesting fixes.",
        "prefilled_args": {"build_id": build_context} if build_context else {},
        "prefilled_prompt": prompt,
        "kind": "composite",
    }
