"""Tool directory and suggestion mediator for the sidebar agent."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from atopile.server.agent.mediator_catalog import (
    _TOOL_DIRECTORY,
    ToolDirectoryItem,
    available_tool_names,
    discovery_tool_names,
    execution_tool_names,
)
from atopile.server.agent.mediator_inference import (
    _extract_context_id,
    _maybe_explain_failure_suggestion,
    _stale_after_seconds,
    _summarize_result,
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


_TERM_BOOST_RULES: list[tuple[tuple[str, ...], dict[str, float]]] = [
    # (search terms, {tool_name: bonus, ...})
    (
        (
            "web",
            "internet",
            "latest",
            "news",
            "look up",
            "external",
            "recent",
            "what changed",
            "release notes",
        ),
        {"web_search": 1.7},
    ),
    (
        (
            "lcsc",
            "jlc",
            "footprint",
            "mcu",
            "sensor",
            "resistor",
            "capacitor",
            "connector",
            "part number",
        ),
        {"parts_search": 1.2, "parts_install": 1.2},
    ),
    (
        ("package", "dependency", "registry", "import"),
        {
            "packages_search": 1.0,
            "packages_install": 1.0,
            "package_ato_list": 1.0,
            "package_ato_search": 1.0,
            "package_ato_read": 1.0,
        },
    ),
    (
        (
            "architecture",
            "structure",
            "hierarchy",
            "module",
            "block diagram",
            "topology",
            "design overview",
        ),
        {"project_list_modules": 1.3, "project_module_children": 1.3},
    ),
    (
        (
            "example",
            "examples",
            "reference",
            "sample",
            "template",
            "how to write ato",
            "ato snippet",
            "similar design",
        ),
        {
            "examples_list": 1.9,
            "examples_search": 1.9,
            "examples_read_ato": 1.9,
            "package_ato_list": 1.9,
            "package_ato_search": 1.9,
            "package_ato_read": 1.9,
        },
    ),
    (
        (
            ".ato/modules",
            "package source",
            "installed module code",
            "reference corpus",
            "package ato",
            "look through package",
            "scan package",
        ),
        {"package_ato_list": 2.2, "package_ato_search": 2.2, "package_ato_read": 2.2},
    ),
    (
        ("bom", "bill of materials", "parts list", "line items", "procurement"),
        {"report_bom": 1.6},
    ),
    (
        ("variables", "parameters", "params", "constraints", "computed values"),
        {"report_variables": 1.6},
    ),
    (
        (
            "generate manufacturing",
            "create manufacturing",
            "manufacturing files",
            "gerber",
            "pick and place",
            "pnp",
            "fabrication package",
            "production files",
        ),
        {"manufacturing_generate": 1.9},
    ),
    (
        ("manufacturing summary", "cost estimate", "mfg summary"),
        {"manufacturing_summary": 1.4},
    ),
    (
        (
            "component position",
            "where is",
            "placement query",
            "atopile address",
            "reference designator",
            "xy",
            "rotation",
        ),
        {"layout_get_component_position": 2.0},
    ),
    (
        (
            "move component",
            "set component position",
            "nudge",
            "rotate component",
            "placement edit",
            "set x",
            "set y",
        ),
        {"layout_set_component_position": 2.0},
    ),
    (
        ("failure",),
        {"build_logs_search": 1.1, "design_diagnostics": 1.1},
    ),
]

_TARGET_BONUS_TOOLS = {
    "build_run",
    "report_bom",
    "report_variables",
    "manufacturing_generate",
    "manufacturing_summary",
}

_DEFAULT_SUGGESTIONS = ("project_read_file", "project_list_modules", "build_run")


def _compute_term_boosts(search_blob: str) -> dict[str, float]:
    """Pre-compute per-tool bonus scores from term-boost rules."""
    boosts: dict[str, float] = {}
    for terms, tool_scores in _TERM_BOOST_RULES:
        if any(term in search_blob for term in terms):
            for tool_name, bonus in tool_scores.items():
                boosts[tool_name] = boosts.get(tool_name, 0.0) + bonus
    return boosts


def suggest_tools(
    *,
    message: str,
    history: list[dict[str, str]],
    selected_targets: list[str],
    tool_memory: dict[str, dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Rank likely tools for a message."""
    text = message.strip().lower()
    context_text = " ".join(
        str(item.get("content", "")).lower() for item in history[-4:]
    ).strip()
    search_blob = text or context_text

    directory = get_tool_directory()
    memory_view = {
        str(item["tool_name"]): item for item in get_tool_memory_view(tool_memory)
    }
    term_boosts = _compute_term_boosts(search_blob)
    has_targets = bool(selected_targets)

    suggestions: list[dict[str, Any]] = []
    for item in directory:
        name = str(item["name"])
        score = term_boosts.get(name, 0.0)

        for keyword in item.get("keywords", []):
            kw = str(keyword).lower()
            if kw and kw in search_blob:
                score += 1.5

        if text and name in text:
            score += 2.0
        if "build" in search_blob and str(item.get("category")) == "build":
            score += 0.7
        if has_targets and name in _TARGET_BONUS_TOOLS:
            score += 0.3

        if score <= 0.0:
            continue

        suggestions.append(
            {
                "name": name,
                "category": item.get("category"),
                "score": round(score, 2),
                "reason": str(item.get("purpose", "")) or f"Likely useful: {name}.",
                "tooltip": item.get("tooltip"),
                "prefilled_args": {},
                "prefilled_prompt": None,
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
        for name in _DEFAULT_SUGGESTIONS:
            item = next((e for e in directory if e["name"] == name), None)
            if item is not None:
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
        key=lambda s: (-float(s.get("score", 0.0)), str(s.get("name", "")))
    )
    return suggestions[: max(1, limit)]


# ----------------------------------------
#                 Tests
# ----------------------------------------

"""Agent mediator tests: tool surfacing, memory, and catalog-derived sets."""


@dataclass
class FakeTrace:
    name: str
    ok: bool
    result: dict


# --- tool directory ---


# --- catalog-derived role sets ---


# --- tool surfacing ---


def _suggestion_names(suggestions: list[dict]) -> set[str]:
    return {s["name"] for s in suggestions}


# --- tool memory ---


class TestAgentMediator:
    def test_get_tool_directory_includes_core_tools(self) -> None:
        directory = get_tool_directory()
        names = {entry["name"] for entry in directory}

        assert "project_read_file" in names
        assert "project_create_path" in names
        assert "project_move_path" in names
        assert "project_delete_path" in names
        assert "build_logs_search" in names
        assert "design_diagnostics" in names
        assert "manufacturing_generate" in names
        assert "layout_run_drc" in names
        assert "examples_list" in names
        assert "examples_search" in names
        assert "examples_read_ato" in names
        assert "package_ato_list" in names
        assert "package_ato_search" in names
        assert "package_ato_read" in names

    def test_discovery_tool_names_includes_read_tools(self) -> None:
        names = discovery_tool_names()
        assert "project_read_file" in names
        assert "project_list_files" in names
        assert "project_search" in names
        assert "stdlib_list" in names
        assert "parts_search" in names
        assert "web_search" in names

    def test_execution_tool_names_includes_edit_tools(self) -> None:
        names = execution_tool_names()
        assert "project_edit_file" in names
        assert "project_create_file" in names
        assert "build_run" in names
        assert "parts_install" in names
        assert "manufacturing_generate" in names

    def test_both_role_tools_appear_in_both_sets(self) -> None:
        disc = discovery_tool_names()
        exec_ = execution_tool_names()
        for tool in ("layout_run_drc",):
            assert tool in disc, f"{tool} missing from discovery"
            assert tool in exec_, f"{tool} missing from execution"

    def test_discovery_and_execution_cover_all_catalog_tools(self) -> None:
        disc = discovery_tool_names()
        exec_ = execution_tool_names()
        all_names = disc | exec_
        directory_names = {entry["name"] for entry in get_tool_directory()}
        assert directory_names <= all_names

    def test_suggest_tools_surfaces_build_logs_for_failure_message(self) -> None:
        suggestions = suggest_tools(
            message="can you inspect build a13d257908e95383 failure logs?",
            history=[],
            selected_targets=[],
            tool_memory={},
        )
        assert "build_logs_search" in _suggestion_names(suggestions)

    def test_suggest_tools_surfaces_parts_for_physical_component_queries(self) -> None:
        suggestions = suggest_tools(
            message="search lcsc stm32f4 mcu part",
            history=[],
            selected_targets=[],
            tool_memory={},
        )
        names = _suggestion_names(suggestions)
        assert "parts_search" in names

    def test_suggest_tools_surfaces_package_creation_for_local_package_requests(
        self,
    ) -> None:
        suggestions = suggest_tools(
            message="create a reusable local package for this lcsc part",
            history=[],
            selected_targets=["default"],
            tool_memory={},
        )
        names = _suggestion_names(suggestions)
        assert "parts_install" in names
        assert "package_create_local" in names

    def test_tool_directory_describes_parts_install_package_flow(self) -> None:
        directory = {entry["name"]: entry for entry in get_tool_directory()}

        assert "create_package=true" in directory["parts_install"]["tooltip"]
        assert (
            "empty local sub-package scaffold"
            in directory["package_create_local"]["purpose"]
        )

    def test_suggest_tools_surfaces_web_search_for_lcsc_id(self) -> None:
        suggestions = suggest_tools(
            message="check datasheet for C521608 and review pin functions",
            history=[],
            selected_targets=["default"],
            tool_memory={},
        )
        assert "web_search" in _suggestion_names(suggestions)

    def test_suggest_tools_surfaces_bom_tool_for_bom_requests(self) -> None:
        suggestions = suggest_tools(
            message="Can you review the BOM and parts list for this target?",
            history=[],
            selected_targets=["default"],
            tool_memory={},
        )
        assert "report_bom" in _suggestion_names(suggestions)

    def test_suggest_tools_surfaces_variables_tool_for_parameter_requests(self) -> None:
        suggestions = suggest_tools(
            message="Show me the computed parameters and constraints",
            history=[],
            selected_targets=["main"],
            tool_memory={},
        )
        assert "report_variables" in _suggestion_names(suggestions)

    def test_suggest_tools_surfaces_module_children_for_hierarchy_requests(
        self,
    ) -> None:
        suggestions = suggest_tools(
            message="inspect hierarchy for src/main.ato:App",
            history=[],
            selected_targets=[],
            tool_memory={},
        )
        names = _suggestion_names(suggestions)
        assert "project_module_children" in names or "project_list_modules" in names

    def test_suggest_tools_surfaces_manufacturing_generate(self) -> None:
        suggestions = suggest_tools(
            message=(
                "generate manufacturing files (gerber + pick and place) "
                "for target default"
            ),
            history=[],
            selected_targets=[],
            tool_memory={},
        )
        assert "manufacturing_generate" in _suggestion_names(suggestions)

    def test_suggest_tools_surfaces_drc_for_drc_requests(self) -> None:
        suggestions = suggest_tools(
            message="run a quick drc check for target default",
            history=[],
            selected_targets=[],
            tool_memory={},
        )
        assert "layout_run_drc" in _suggestion_names(suggestions)

    def test_suggest_tools_surfaces_examples_search(self) -> None:
        suggestions = suggest_tools(
            message="show an example of i2c module templating in ato",
            history=[],
            selected_targets=[],
            tool_memory={},
        )
        assert "examples_search" in _suggestion_names(suggestions)

    def test_suggest_tools_surfaces_package_ato_search(self) -> None:
        suggestions = suggest_tools(
            message="search package ato source for regulator enable pattern",
            history=[],
            selected_targets=[],
            tool_memory={},
        )
        assert "package_ato_search" in _suggestion_names(suggestions)

    def test_tool_memory_view_marks_stale_entries(self) -> None:
        now = time.time()
        memory = {
            "build_logs_search": {
                "tool_name": "build_logs_search",
                "summary": "no output",
                "ok": False,
                "updated_at": now - 200.0,
                "context_id": "a13d257908e95383",
            }
        }
        view = get_tool_memory_view(memory)

        assert len(view) == 1
        assert view[0]["stale"] is True
        assert "rerun?" in str(view[0]["stale_hint"])

    def test_update_tool_memory_summarizes_results(self) -> None:
        traces = [
            FakeTrace(
                name="project_edit_file",
                ok=True,
                result={"operations_applied": 2, "first_changed_line": 9},
            )
        ]
        updated = update_tool_memory({}, traces)
        entry = updated["project_edit_file"]

        assert entry["tool_name"] == "project_edit_file"
        assert entry["ok"] is True
        assert "edits applied" in entry["summary"]
