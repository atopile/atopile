"""Tool directory and suggestion mediator for the sidebar agent."""

from __future__ import annotations

import re
import time
from typing import Any

from atopile.server.agent import tools
from atopile.server.agent.mediator_catalog import (
    _TOOL_DIRECTORY,
    ToolDirectoryItem,
    available_tool_names,
    get_tool_directory_items,
)
from atopile.server.agent.mediator_inference import (
    _extract_context_id,
    _infer_prefilled_args,
    _maybe_explain_failure_suggestion,
    _prefilled_prompt,
    _reason_from_matches,
    _stale_after_seconds,
    _summarize_result,
)


_BUILD_ID_RE = re.compile(r"\b[a-f0-9]{8,}\b", re.IGNORECASE)
_AUTOLAYOUT_JOB_ID_RE = re.compile(r"\bal-[a-f0-9]{12}\b", re.IGNORECASE)
_FILE_RE = re.compile(r"([A-Za-z0-9_./-]+\.(?:ato|py|md|json|yaml|yml|toml|ts|tsx))")
_PDF_FILE_RE = re.compile(r"([A-Za-z0-9_./-]+\.pdf)\b", re.IGNORECASE)
_LCSC_RE = re.compile(r"\bC\d{3,}\b", re.IGNORECASE)
_ENTRY_POINT_RE = re.compile(r"([A-Za-z0-9_./-]+\.ato:[A-Za-z_][A-Za-z0-9_]*)")
_PACKAGE_RE = re.compile(
    r"\b([a-z0-9_.-]+/[a-z0-9_.-]+)(?:@([^\s]+))?\b",
    re.IGNORECASE,
)


def get_tool_directory() -> list[dict[str, Any]]:
    """Return directory metadata for all currently advertised tools."""
    directory: list[dict[str, Any]] = []
    for name in available_tool_names():
        item = _TOOL_DIRECTORY.get(name)
        if item is None:
            item = ToolDirectoryItem(
                name=name,
                category="other",
                purpose=name.replace("_", " "),
                tooltip=f"Use {name.replace('_', ' ')}.",
                inputs=[],
                typical_output="result",
                keywords=[name],
            )
        directory.append(
            {
                "name": item.name,
                "category": item.category,
                "purpose": item.purpose,
                "tooltip": item.tooltip,
                "inputs": item.inputs,
                "typical_output": item.typical_output,
                "keywords": item.keywords,
            }
        )
    directory.sort(key=lambda entry: (str(entry["category"]), str(entry["name"])))
    return directory


def update_tool_memory(
    current_memory: dict[str, dict[str, Any]],
    traces: list[Any],
) -> dict[str, dict[str, Any]]:
    """Update per-tool memory entries from a turn's tool traces."""
    updated = dict(current_memory)
    now = time.time()

    for trace in traces:
        name = getattr(trace, "name", None)
        if not isinstance(name, str) or not name:
            continue
        ok = bool(getattr(trace, "ok", False))
        result = getattr(trace, "result", {})
        if not isinstance(result, dict):
            result = {}

        summary = _summarize_result(name, ok, result)
        context_id = _extract_context_id(result)

        updated[name] = {
            "tool_name": name,
            "summary": summary,
            "ok": ok,
            "updated_at": now,
            "context_id": context_id,
        }

    return updated


def get_tool_memory_view(
    current_memory: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return memory entries with stale markers for UI."""
    now = time.time()
    entries: list[dict[str, Any]] = []
    for raw in current_memory.values():
        name = str(raw.get("tool_name", ""))
        updated_at = float(raw.get("updated_at", 0.0) or 0.0)
        age_s = max(0.0, now - updated_at) if updated_at else 0.0
        stale_after_s = _stale_after_seconds(name)
        is_stale = age_s > stale_after_s
        context_id = raw.get("context_id")
        stale_hint = None
        if is_stale:
            if isinstance(context_id, str) and context_id:
                stale_hint = f"result from {context_id}; rerun?"
            else:
                stale_hint = "result may be stale; rerun?"

        entries.append(
            {
                "tool_name": name,
                "summary": str(raw.get("summary", "")),
                "ok": bool(raw.get("ok", False)),
                "updated_at": updated_at,
                "age_seconds": round(age_s, 1),
                "stale": is_stale,
                "stale_hint": stale_hint,
                "context_id": context_id,
            }
        )

    entries.sort(key=lambda entry: float(entry.get("updated_at", 0.0)), reverse=True)
    return entries


def suggest_tools(
    *,
    message: str,
    history: list[dict[str, str]],
    selected_targets: list[str],
    tool_memory: dict[str, dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Rank likely tools for a message and provide argument/prompt hints."""
    text = message.strip().lower()
    context_text = " ".join(
        str(item.get("content", "")).lower() for item in history[-4:]
    ).strip()
    search_blob = text if text else context_text

    suggestions: list[dict[str, Any]] = []
    directory = get_tool_directory()
    memory_view = {
        str(item["tool_name"]): item for item in get_tool_memory_view(tool_memory)
    }

    for item in directory:
        name = str(item["name"])
        keywords = [str(keyword).lower() for keyword in item.get("keywords", [])]
        score = 0.0
        matched: list[str] = []

        for keyword in keywords:
            if keyword and keyword in search_blob:
                score += 1.5
                matched.append(keyword)

        if text and name in text:
            score += 2.0
            matched.append(name)

        if "build" in search_blob and str(item.get("category")) == "build":
            score += 0.7
        web_terms = (
            "web",
            "internet",
            "latest",
            "news",
            "look up",
            "external",
            "recent",
            "what changed",
            "release notes",
        )
        if any(term in search_blob for term in web_terms) and name == "web_search":
            score += 1.7
        physical_part_terms = (
            "lcsc",
            "jlc",
            "footprint",
            "mcu",
            "sensor",
            "resistor",
            "capacitor",
            "connector",
            "part number",
        )
        if any(term in search_blob for term in physical_part_terms) and name in {
            "parts_search",
            "parts_install",
        }:
            score += 1.2
        package_terms = ("package", "dependency", "registry", "import")
        if any(term in search_blob for term in package_terms) and name in {
            "packages_search",
            "packages_install",
            "package_ato_list",
            "package_ato_search",
            "package_ato_read",
        }:
            score += 1.0
        structure_terms = (
            "architecture",
            "structure",
            "hierarchy",
            "module",
            "block diagram",
            "topology",
            "design overview",
        )
        if any(term in search_blob for term in structure_terms) and name in {
            "project_list_modules",
            "project_module_children",
        }:
            score += 1.3
        example_terms = (
            "example",
            "examples",
            "reference",
            "sample",
            "template",
            "how to write ato",
            "ato snippet",
            "similar design",
        )
        if any(term in search_blob for term in example_terms) and name in {
            "examples_list",
            "examples_search",
            "examples_read_ato",
            "package_ato_list",
            "package_ato_search",
            "package_ato_read",
        }:
            score += 1.9
        package_source_terms = (
            ".ato/modules",
            "package source",
            "installed module code",
            "reference corpus",
            "package ato",
            "look through package",
            "scan package",
        )
        if any(term in search_blob for term in package_source_terms) and name in {
            "package_ato_list",
            "package_ato_search",
            "package_ato_read",
        }:
            score += 2.2
        bom_terms = (
            "bom",
            "bill of materials",
            "parts list",
            "line items",
            "procurement",
        )
        if any(term in search_blob for term in bom_terms) and name == "report_bom":
            score += 1.6
        parameter_terms = (
            "variables",
            "parameters",
            "params",
            "constraints",
            "computed values",
        )
        if (
            any(term in search_blob for term in parameter_terms)
            and name == "report_variables"
        ):
            score += 1.6
        mfg_generate_terms = (
            "generate manufacturing",
            "create manufacturing",
            "manufacturing files",
            "gerber",
            "pick and place",
            "pnp",
            "fabrication package",
            "production files",
        )
        if (
            any(term in search_blob for term in mfg_generate_terms)
            and name == "manufacturing_generate"
        ):
            score += 1.9
        mfg_summary_terms = ("manufacturing summary", "cost estimate", "mfg summary")
        if (
            any(term in search_blob for term in mfg_summary_terms)
            and name == "manufacturing_summary"
        ):
            score += 1.4
        autolayout_terms = (
            "autolayout",
            "auto layout",
            "autoroute",
            "route board",
            "routing",
            "placement",
            "deeppcb",
            "pcb layout",
        )
        if any(term in search_blob for term in autolayout_terms):
            if name == "autolayout_run":
                score += 1.9
            elif name in {"autolayout_status", "autolayout_fetch_to_layout"}:
                score += 1.3
            elif name == "autolayout_configure_board_intent":
                score += 1.1
        stackup_terms = (
            "ground pour",
            "ground plane",
            "power plane",
            "stackup",
            "board thickness",
            "copper weight",
            "dielectric",
            "impedance",
            "controlled impedance",
        )
        if (
            any(term in search_blob for term in stackup_terms)
            and name == "autolayout_configure_board_intent"
        ):
            score += 2.1
        fetch_terms = (
            "fetch routed",
            "fetch placement",
            "apply candidate",
            "pull layout",
            "archive iteration",
        )
        if (
            any(term in search_blob for term in fetch_terms)
            and name == "autolayout_fetch_to_layout"
        ):
            score += 1.8
        screenshot_terms = (
            "screenshot",
            "render board",
            "board image",
            "2d image",
            "3d image",
            "board preview",
        )
        if (
            any(term in search_blob for term in screenshot_terms)
            and name == "autolayout_request_screenshot"
        ):
            score += 1.9
        placement_query_terms = (
            "component position",
            "where is",
            "placement query",
            "atopile address",
            "reference designator",
            "xy",
            "rotation",
        )
        if (
            any(term in search_blob for term in placement_query_terms)
            and name == "layout_get_component_position"
        ):
            score += 2.0
        placement_edit_terms = (
            "move component",
            "set component position",
            "nudge",
            "rotate component",
            "placement edit",
            "set x",
            "set y",
        )
        if (
            any(term in search_blob for term in placement_edit_terms)
            and name == "layout_set_component_position"
        ):
            score += 2.0
        if "failure" in search_blob and name in {
            "build_logs_search",
            "design_diagnostics",
        }:
            score += 1.1
        if selected_targets and name in {
            "build_run",
            "report_bom",
            "report_variables",
            "manufacturing_generate",
            "manufacturing_summary",
            "autolayout_run",
            "autolayout_request_screenshot",
            "autolayout_configure_board_intent",
        }:
            score += 0.3

        prefilled_args = _infer_prefilled_args(
            tool_name=name,
            message=message,
            selected_targets=selected_targets,
            memory_view=memory_view,
        )
        if prefilled_args:
            score += 0.8

        if score <= 0.0:
            continue

        reason = _reason_from_matches(
            name=name,
            matched_keywords=matched,
            default_reason=str(item.get("purpose", "")),
        )
        prefilled_prompt = _prefilled_prompt(name, prefilled_args)

        suggestions.append(
            {
                "name": name,
                "category": item.get("category"),
                "score": round(score, 2),
                "reason": reason,
                "tooltip": item.get("tooltip"),
                "prefilled_args": prefilled_args,
                "prefilled_prompt": prefilled_prompt,
                "kind": "tool",
            }
        )

    composite = _maybe_explain_failure_suggestion(
        message=message,
        memory_view=memory_view,
    )
    if composite:
        suggestions.append(composite)

    if not suggestions and text:
        defaults = ["project_read_file", "project_list_modules", "build_run"]
        for name in defaults:
            item = next((entry for entry in directory if entry["name"] == name), None)
            if item is None:
                continue
            suggestions.append(
                {
                    "name": name,
                    "category": item.get("category"),
                    "score": 0.5,
                    "reason": str(item.get("purpose", "")),
                    "tooltip": item.get("tooltip"),
                    "prefilled_args": {},
                    "prefilled_prompt": None,
                    "kind": "tool",
                }
            )

    suggestions.sort(
        key=lambda suggestion: (
            -float(suggestion.get("score", 0.0)),
            str(suggestion.get("name", "")),
        )
    )
    return suggestions[: max(1, limit)]

