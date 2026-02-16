"""Inference and summarization helpers for the agent mediator."""

from __future__ import annotations

import re
from typing import Any

from atopile.server.agent.mediator_catalog import _TOOL_DIRECTORY

def _stale_after_seconds(tool_name: str) -> float:
    if tool_name.startswith("build") or tool_name.startswith("design_"):
        return 90.0
    if tool_name.startswith("autolayout_"):
        return 75.0
    if tool_name.startswith("layout_"):
        return 120.0
    if tool_name.startswith("project_"):
        return 300.0
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
        "fallback_job_id",
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


def _summarize_result(name: str, ok: bool, result: dict[str, Any]) -> str:
    if not ok:
        error = result.get("error")
        if isinstance(error, str) and error:
            return _trim(error, 120)
        return "failed"

    message = result.get("message")
    if isinstance(message, str) and message:
        return _trim(message, 120)
    total = result.get("total")
    if isinstance(total, int):
        return f"{total} items"
    ops = result.get("operations_applied")
    if isinstance(ops, int):
        return f"{ops} edits applied"
    if name == "build_run":
        targets = result.get("build_targets")
        if isinstance(targets, list):
            return f"{len(targets)} build(s) queued"
    if name == "autolayout_run":
        state = result.get("state")
        if isinstance(state, str) and state:
            return f"autolayout {state}"
        return "autolayout job queued"
    if name == "autolayout_status":
        state = result.get("state")
        candidate_count = result.get("candidate_count")
        if isinstance(state, str):
            if isinstance(candidate_count, int):
                return f"state={state}; candidates={candidate_count}"
            return f"state={state}"
        latest_job = result.get("latest_job_id")
        total_jobs = result.get("total_jobs")
        if isinstance(latest_job, str) and latest_job:
            if isinstance(total_jobs, int):
                return f"latest job={latest_job}; total={total_jobs}"
            return f"latest job={latest_job}"
    if name == "autolayout_fetch_to_layout":
        candidate = result.get("selected_candidate_id")
        if isinstance(candidate, str) and candidate:
            return f"applied {candidate}"
        if result.get("ready_to_apply") is False:
            state = result.get("state")
            if isinstance(state, str) and state:
                return f"waiting ({state})"
        return "layout candidate applied"
    if name == "autolayout_request_screenshot":
        view = result.get("view")
        if isinstance(view, str) and view:
            return f"{view} screenshot rendered"
        return "screenshot rendered"
    if name == "layout_run_drc":
        errors = result.get("error_count")
        total = result.get("total_findings")
        if isinstance(errors, int) and isinstance(total, int):
            return f"drc: {errors} error(s), {total} finding(s)"
        return "drc report generated"
    if name == "autolayout_configure_board_intent":
        target = result.get("build_target")
        if isinstance(target, str) and target:
            return f"board intent updated for {target}"
        return "board intent updated"
    if name == "web_search":
        count = result.get("returned_results")
        query = result.get("query")
        if isinstance(count, int):
            if isinstance(query, str) and query.strip():
                return f"{count} web results for '{_trim(query.strip(), 30)}'"
            return f"{count} web results"
        return "web search complete"
    if name == "layout_get_component_position":
        if bool(result.get("found", False)):
            component = result.get("component")
            if isinstance(component, dict):
                reference = component.get("reference")
                if isinstance(reference, str) and reference:
                    return f"position for {reference}"
            return "component position fetched"
        suggestions = result.get("suggestions")
        if isinstance(suggestions, list):
            return f"not found; {len(suggestions)} suggestion(s)"
        return "component not found"
    if name == "layout_set_component_position":
        if bool(result.get("updated", False)):
            after = result.get("after")
            if isinstance(after, dict):
                reference = after.get("reference")
                if isinstance(reference, str) and reference:
                    return f"moved {reference}"
            return "component placement updated"
        suggestions = result.get("suggestions")
        if isinstance(suggestions, list):
            return f"not found; {len(suggestions)} suggestion(s)"
        return "component placement not updated"
    return "ok"


def _trim(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _reason_from_matches(
    *,
    name: str,
    matched_keywords: list[str],
    default_reason: str,
) -> str:
    if matched_keywords:
        keyword = matched_keywords[0]
        return f"Matches '{keyword}' intent for {name}."
    return default_reason or f"Likely useful: {name}."


def _prefilled_prompt(tool_name: str, prefilled_args: dict[str, Any]) -> str | None:
    if not prefilled_args:
        return None
    return f"Use `{tool_name}` with arguments: {prefilled_args}"


def _infer_prefilled_args(
    *,
    tool_name: str,
    message: str,
    selected_targets: list[str],
    memory_view: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    text = message.strip()
    lower = text.lower()
    known_examples = {
        "quickstart",
        "passives",
        "equations",
        "pick_parts",
        "i2c",
        "esp32_minimal",
        "layout_reuse",
        "led_badge",
        "fabll_minimal",
    }

    if tool_name == "project_search":
        quoted = re.search(r"['\"]([^'\"]+)['\"]", text)
        if quoted:
            return {"query": quoted.group(1)}
        find_for = re.search(r"(?:search|find|grep)\s+(?:for\s+)?(.+)", lower)
        if find_for:
            query = find_for.group(1).strip().strip(".")
            if query:
                return {"query": query}

    if tool_name == "web_search":
        quoted = re.search(r"['\"]([^'\"]+)['\"]", text)
        if quoted:
            return {"query": quoted.group(1), "num_results": 8, "search_type": "auto"}
        cleaned = re.sub(
            r"\b(web|internet|latest|news|look up|lookup|search|external)\b",
            " ",
            lower,
        )
        query = " ".join(cleaned.split()).strip().strip(".")
        if query:
            return {"query": query, "num_results": 8, "search_type": "auto"}
        return {
            "query": "atopile latest updates",
            "num_results": 8,
            "search_type": "auto",
        }

    if tool_name == "examples_list":
        return {"limit": 20}

    if tool_name == "examples_search":
        quoted = re.search(r"['\"]([^'\"]+)['\"]", text)
        if quoted:
            return {"query": quoted.group(1), "limit": 80}

        cleaned = re.sub(
            r"\b(example|examples|reference|sample|snippet|ato|show|find|search)\b",
            " ",
            lower,
        )
        query = " ".join(cleaned.split()).strip(".")
        if query:
            return {"query": query, "limit": 80}
        return {"query": "module", "limit": 80}

    if tool_name == "examples_read_ato":
        example_match = re.search(r"\bexamples/([a-z0-9_.-]+)\b", lower)
        if example_match:
            return {
                "example": example_match.group(1),
                "start_line": 1,
                "max_lines": 220,
            }
        for example_name in known_examples:
            if re.search(rf"\b{re.escape(example_name)}\b", lower):
                return {"example": example_name, "start_line": 1, "max_lines": 220}

    if tool_name == "package_ato_list":
        args: dict[str, Any] = {}
        package_match = _PACKAGE_RE.search(text)
        if package_match:
            args["package_query"] = package_match.group(1)
        return args

    if tool_name == "package_ato_search":
        args: dict[str, Any] = {}
        package_match = _PACKAGE_RE.search(text)
        if package_match:
            args["package_query"] = package_match.group(1)
        quoted = re.search(r"['\"]([^'\"]+)['\"]", text)
        if quoted:
            args["query"] = quoted.group(1)
            return args
        cleaned = re.sub(
            r"\b(package|packages|ato|search|find|look|through|scan|source|code)\b",
            " ",
            lower,
        )
        query = " ".join(cleaned.split()).strip(".")
        if query:
            args["query"] = query
            return args
        args["query"] = "module"
        return args

    if tool_name == "package_ato_read":
        args: dict[str, Any] = {}
        package_match = _PACKAGE_RE.search(text)
        if package_match:
            args["package_identifier"] = package_match.group(1)
        file_match = re.search(r"([A-Za-z0-9_./-]+\.ato)\b", text)
        if file_match:
            args["path_in_package"] = file_match.group(1)
        return args

    if tool_name == "project_read_file":
        file_match = _FILE_RE.search(text)
        if file_match:
            return {"path": file_match.group(1), "start_line": 1, "max_lines": 220}

    if tool_name == "project_module_children":
        entry_match = _ENTRY_POINT_RE.search(text)
        if entry_match:
            return {"entry_point": entry_match.group(1), "max_depth": 2}

    if tool_name == "layout_get_component_position":
        args: dict[str, Any] = {}
        if selected_targets:
            args["target"] = selected_targets[0]
        quoted = re.search(r"['\"]([^'\"]+)['\"]", text)
        if quoted:
            args["address"] = quoted.group(1)
            return args
        address_match = re.search(
            r"\b(?:app|module|board|root|top)\.[a-z0-9_.:-]+\b",
            lower,
        )
        if address_match:
            args["address"] = address_match.group(0)
            return args

    if tool_name == "layout_set_component_position":
        args: dict[str, Any] = {"mode": "absolute"}
        if selected_targets:
            args["target"] = selected_targets[0]
        quoted = re.search(r"['\"]([^'\"]+)['\"]", text)
        if quoted:
            args["address"] = quoted.group(1)
        else:
            address_match = re.search(
                r"\b(?:app|module|board|root|top)\.[a-z0-9_.:-]+\b",
                lower,
            )
            if address_match:
                args["address"] = address_match.group(0)

        nudge_match = re.search(
            r"\bnudge\s+([+-]?\d+(?:\.\d+)?)\s*mm\s+"
            r"(left|right|up|down|top|bottom)\b",
            lower,
        )
        if nudge_match:
            amount = float(nudge_match.group(1))
            direction = nudge_match.group(2)
            dx = 0.0
            dy = 0.0
            if direction == "left":
                dx = -amount
            elif direction == "right":
                dx = amount
            elif direction in {"up", "top"}:
                dy = -amount
            else:
                dy = amount
            args["mode"] = "relative"
            args["dx_mm"] = dx
            args["dy_mm"] = dy
            return args

    if tool_name == "build_logs_search":
        requested_levels: list[str] = []
        if "debug" in lower:
            requested_levels.append("DEBUG")
        if "info" in lower:
            requested_levels.append("INFO")
        if "warn" in lower:
            requested_levels.append("WARNING")
        if "error" in lower or "fail" in lower:
            requested_levels.append("ERROR")
        if "alert" in lower:
            requested_levels.append("ALERT")

        deduped_levels: list[str] = []
        for level in requested_levels:
            if level not in deduped_levels:
                deduped_levels.append(level)

        stage_match = re.search(r"(?:stage|phase)\s+([a-z0-9_.-]+)", lower)
        build_id_match = _BUILD_ID_RE.search(lower)
        if build_id_match:
            args: dict[str, Any] = {"build_id": build_id_match.group(0)}
            if "error" in lower or "fail" in lower:
                args["query"] = "error"
            if deduped_levels:
                args["log_levels"] = deduped_levels
            if stage_match:
                args["stage"] = stage_match.group(1)
            if "user logs" in lower:
                args["audience"] = "user"
            elif "developer logs" in lower:
                args["audience"] = "developer"
            return args
        recent = memory_view.get("build_run")
        if recent and isinstance(recent.get("context_id"), str):
            args = {"build_id": str(recent["context_id"])}
            if deduped_levels:
                args["log_levels"] = deduped_levels
            if stage_match:
                args["stage"] = stage_match.group(1)
            return args

    if tool_name == "autolayout_run":
        args: dict[str, Any] = {}
        if selected_targets:
            args["build_target"] = selected_targets[0]
        else:
            target_match = re.search(r"(?:target|build)\s+([a-z0-9_.-]+)\b", lower)
            if target_match:
                candidate = target_match.group(1)
                if candidate not in {"for", "with", "from", "the"}:
                    args["build_target"] = candidate

        if "placement" in lower or "place components" in lower:
            args["job_type"] = "Placement"
        else:
            args["job_type"] = "Routing"

        if "keep existing" in lower or "protected wiring" in lower:
            args["routing_type"] = "CurrentProtectedWiring"
        elif "start from current" in lower:
            args["routing_type"] = "CurrentUnprotectedWiring"
        elif "empty board" in lower or "fresh routing" in lower:
            args["routing_type"] = "EmptyBoard"

        resume_id = re.search(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
            r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
            lower,
            re.IGNORECASE,
        )
        if resume_id and ("resume" in lower or "from board" in lower):
            args["resume_board_id"] = resume_id.group(0)
        return args

    if tool_name == "autolayout_status":
        args: dict[str, Any] = {}
        if any(token in lower for token in ("periodic", "check in", "monitor", "wait")):
            args["wait_seconds"] = 120
            args["poll_interval_seconds"] = 15
        job_match = _AUTOLAYOUT_JOB_ID_RE.search(lower)
        if job_match:
            args["job_id"] = job_match.group(0)
            return args
        for memory_key in (
            "autolayout_fetch_to_layout",
            "autolayout_status",
            "autolayout_run",
        ):
            recent = memory_view.get(memory_key)
            if recent and isinstance(recent.get("context_id"), str):
                args["job_id"] = str(recent["context_id"])
                return args

    if tool_name == "autolayout_fetch_to_layout":
        job_match = _AUTOLAYOUT_JOB_ID_RE.search(lower)
        if job_match:
            return {"job_id": job_match.group(0)}
        for memory_key in (
            "autolayout_status",
            "autolayout_fetch_to_layout",
            "autolayout_run",
        ):
            recent = memory_view.get(memory_key)
            if recent and isinstance(recent.get("context_id"), str):
                return {"job_id": str(recent["context_id"])}

    if tool_name == "autolayout_request_screenshot":
        args = {"view": "2d"}
        if "3d" in lower and "2d" in lower:
            args["view"] = "both"
        elif "3d" in lower:
            args["view"] = "3d"
        elif "both" in lower:
            args["view"] = "both"
        if "bottom" in lower or "back side" in lower or "backside" in lower:
            args["side"] = "bottom"
        elif "both sides" in lower:
            args["side"] = "both"
        else:
            args["side"] = "top"

        highlight_match = re.search(
            r"(?:highlight|focus on|spotlight)\s+(?:component\s+)?([a-z0-9_.:-]+)\b",
            lower,
        )
        if highlight_match:
            args["highlight_components"] = [highlight_match.group(1)]
            args["dim_others"] = True

        if selected_targets:
            args["target"] = selected_targets[0]
        else:
            target_match = re.search(r"(?:target|build)\s+([a-z0-9_.-]+)\b", lower)
            if target_match:
                candidate = target_match.group(1)
                if candidate not in {"for", "with", "from", "the"}:
                    args["target"] = candidate
        return args

    if tool_name == "layout_run_drc":
        args: dict[str, Any] = {}
        if selected_targets:
            args["target"] = selected_targets[0]
        else:
            target_match = re.search(r"(?:target|build)\s+([a-z0-9_.-]+)\b", lower)
            if target_match:
                candidate = target_match.group(1)
                if candidate not in {"for", "with", "from", "the"}:
                    args["target"] = candidate
        if "quick" in lower or "fast" in lower:
            args["max_findings"] = 40
        return args

    if tool_name == "autolayout_configure_board_intent":
        args: dict[str, Any] = {}
        if selected_targets:
            args["build_target"] = selected_targets[0]

        if "no ground pour" in lower or "disable pour" in lower:
            args["enable_ground_pours"] = False
        elif any(
            token in lower for token in ("ground pour", "ground plane", "power plane")
        ):
            args["enable_ground_pours"] = True

        if "hatched" in lower:
            args["plane_mode"] = "hatched"
        elif "solid" in lower:
            args["plane_mode"] = "solid"

        if "4 layer" in lower or "4-layer" in lower:
            args["layer_count"] = 4
        elif "6 layer" in lower or "6-layer" in lower:
            args["layer_count"] = 6
        elif "2 layer" in lower or "2-layer" in lower:
            args["layer_count"] = 2

        if "1.6mm" in lower:
            args["board_thickness_mm"] = 1.6
        elif "0.8mm" in lower:
            args["board_thickness_mm"] = 0.8
        elif "1.0mm" in lower:
            args["board_thickness_mm"] = 1.0

        if "preserve existing routing" in lower:
            args["preserve_existing_routing"] = True
        elif "ignore existing routing" in lower:
            args["preserve_existing_routing"] = False

        if args:
            return args

    if tool_name == "parts_install":
        lcsc_match = _LCSC_RE.search(text)
        if lcsc_match:
            return {"lcsc_id": lcsc_match.group(0).upper()}

    if tool_name == "datasheet_read":
        default_target = selected_targets[0] if selected_targets else None
        lcsc_match = _LCSC_RE.search(text)
        if lcsc_match:
            args = {"lcsc_id": lcsc_match.group(0).upper()}
            if default_target:
                args["target"] = default_target
            return args

        url_match = re.search(r"https?://\S+", text)
        if url_match:
            url = url_match.group(0).rstrip(".,);]>")
            if url:
                args = {"url": url}
                if default_target:
                    args["target"] = default_target
                return args

        pdf_match = _PDF_FILE_RE.search(text)
        if pdf_match:
            args = {"path": pdf_match.group(1)}
            if default_target:
                args["target"] = default_target
            return args

    if tool_name == "parts_search":
        triggers = (
            "part",
            "component",
            "lcsc",
            "jlc",
            "mcu",
            "sensor",
            "resistor",
            "capacitor",
            "connector",
            "footprint",
        )
        if any(token in lower for token in triggers):
            cleaned = re.sub(
                r"\b(search|find|lookup|for|part|parts|component|components)\b",
                " ",
                lower,
            )
            query = " ".join(cleaned.split()).strip(".")
            if query:
                return {"query": query}

    if tool_name == "packages_install":
        package_match = _PACKAGE_RE.search(text)
        if package_match:
            identifier = package_match.group(1)
            version = package_match.group(2)
            if version:
                return {"identifier": identifier, "version": version}
            return {"identifier": identifier}

    if tool_name == "build_run":
        if selected_targets:
            return {"targets": [selected_targets[0]]}
        if "build" in lower:
            return {"targets": []}

    if tool_name == "manufacturing_generate":
        args: dict[str, Any] = {"include_targets": ["mfg-data"]}
        if selected_targets:
            args["target"] = selected_targets[0]
            return args
        target_match = re.search(r"(?:target|build)\s+([a-z0-9_.-]+)\b", lower)
        if target_match:
            candidate = target_match.group(1)
            if candidate not in {"for", "with", "from", "the"}:
                args["target"] = candidate
        return args

    if tool_name in {
        "report_bom",
        "report_variables",
        "manufacturing_summary",
        "manufacturing_generate",
    }:
        if selected_targets:
            return {"target": selected_targets[0]}
        target_match = re.search(r"(?:target|build)\s+([a-z0-9_.-]+)\b", lower)
        if target_match:
            candidate = target_match.group(1)
            if candidate not in {"for", "with", "from", "the"}:
                return {"target": candidate}

    return {}


def _maybe_explain_failure_suggestion(
    *,
    message: str,
    memory_view: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    text = message.strip().lower()
    trigger = any(
        phrase in text
        for phrase in (
            "explain failure",
            "why did it fail",
            "diagnose",
            "debug build",
            "lint current design",
        )
    )
    if not trigger and text:
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
        "tooltip": ("Runs diagnostics-first failure analysis before suggesting fixes."),
        "prefilled_args": {"build_id": build_context} if build_context else {},
        "prefilled_prompt": prompt,
        "kind": "composite",
    }
