from __future__ import annotations

import time
from dataclasses import dataclass

from atopile.server.agent import mediator


@dataclass
class FakeTrace:
    name: str
    ok: bool
    result: dict


def test_get_tool_directory_includes_core_tools() -> None:
    directory = mediator.get_tool_directory()
    names = {entry["name"] for entry in directory}

    assert "project_read_file" in names
    assert "datasheet_read" in names
    assert "project_rename_path" in names
    assert "project_delete_path" in names
    assert "build_logs_search" in names
    assert "design_diagnostics" in names


def test_suggest_tools_prefills_build_logs_from_message() -> None:
    suggestions = mediator.suggest_tools(
        message="can you inspect build a13d257908e95383 failure logs?",
        history=[],
        selected_targets=[],
        tool_memory={},
    )

    build_logs = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "build_logs_search"
        ),
        None,
    )
    assert build_logs is not None
    assert build_logs["prefilled_args"]["build_id"] == "a13d257908e95383"


def test_tool_memory_view_marks_stale_entries() -> None:
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
    view = mediator.get_tool_memory_view(memory)

    assert len(view) == 1
    assert view[0]["stale"] is True
    assert "rerun?" in str(view[0]["stale_hint"])


def test_update_tool_memory_summarizes_results() -> None:
    traces = [
        FakeTrace(
            name="project_edit_file",
            ok=True,
            result={"operations_applied": 2, "first_changed_line": 9},
        )
    ]
    updated = mediator.update_tool_memory({}, traces)
    entry = updated["project_edit_file"]

    assert entry["tool_name"] == "project_edit_file"
    assert entry["ok"] is True
    assert "edits applied" in entry["summary"]


def test_suggest_tools_prefers_parts_for_physical_component_queries() -> None:
    suggestions = mediator.suggest_tools(
        message="search lcsc stm32f4 mcu part",
        history=[],
        selected_targets=[],
        tool_memory={},
    )

    parts = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "parts_search"
        ),
        None,
    )
    packages = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "packages_search"
        ),
        None,
    )

    assert parts is not None
    assert parts["prefilled_args"].get("query")
    if packages is not None:
        assert float(parts["score"]) >= float(packages["score"])


def test_suggest_tools_prefills_debug_log_filters() -> None:
    suggestions = mediator.suggest_tools(
        message="show debug logs for build a13d257908e95383 stage compile",
        history=[],
        selected_targets=[],
        tool_memory={},
    )

    build_logs = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "build_logs_search"
        ),
        None,
    )
    assert build_logs is not None
    assert build_logs["prefilled_args"]["build_id"] == "a13d257908e95383"
    assert build_logs["prefilled_args"]["log_levels"] == ["DEBUG"]
    assert build_logs["prefilled_args"]["stage"] == "compile"


def test_suggest_tools_prefills_datasheet_read_from_lcsc_id() -> None:
    suggestions = mediator.suggest_tools(
        message="check datasheet for C521608 and review pin functions",
        history=[],
        selected_targets=["default"],
        tool_memory={},
    )

    datasheet = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "datasheet_read"
        ),
        None,
    )
    assert datasheet is not None
    assert datasheet["prefilled_args"]["lcsc_id"] == "C521608"
    assert datasheet["prefilled_args"]["target"] == "default"


def test_suggest_tools_surfaces_bom_tool_for_bom_requests() -> None:
    suggestions = mediator.suggest_tools(
        message="Can you review the BOM and parts list for this target?",
        history=[],
        selected_targets=["default"],
        tool_memory={},
    )

    bom = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "report_bom"
        ),
        None,
    )
    assert bom is not None
    assert bom["prefilled_args"]["target"] == "default"


def test_suggest_tools_surfaces_variables_tool_for_parameter_requests() -> None:
    suggestions = mediator.suggest_tools(
        message="Show me the computed parameters and constraints",
        history=[],
        selected_targets=["main"],
        tool_memory={},
    )

    variables = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "report_variables"
        ),
        None,
    )
    assert variables is not None
    assert variables["prefilled_args"]["target"] == "main"


def test_suggest_tools_prefills_module_children_from_entry_point() -> None:
    suggestions = mediator.suggest_tools(
        message="inspect hierarchy for src/main.ato:App",
        history=[],
        selected_targets=[],
        tool_memory={},
    )

    module_children = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "project_module_children"
        ),
        None,
    )
    assert module_children is not None
    assert module_children["prefilled_args"]["entry_point"] == "src/main.ato:App"
