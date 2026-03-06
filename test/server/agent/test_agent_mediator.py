"""Agent mediator tests: tool surfacing, memory, and catalog-derived sets."""

import time
from dataclasses import dataclass

from atopile.server.agent import mediator
from atopile.server.agent.mediator_catalog import (
    discovery_tool_names,
    execution_tool_names,
)


@dataclass
class FakeTrace:
    name: str
    ok: bool
    result: dict


# --- tool directory ---


def test_get_tool_directory_includes_core_tools() -> None:
    directory = mediator.get_tool_directory()
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


# --- catalog-derived role sets ---


def test_discovery_tool_names_includes_read_tools() -> None:
    names = discovery_tool_names()
    assert "project_read_file" in names
    assert "project_list_files" in names
    assert "project_search" in names
    assert "stdlib_list" in names
    assert "parts_search" in names
    assert "web_search" in names


def test_execution_tool_names_includes_edit_tools() -> None:
    names = execution_tool_names()
    assert "project_edit_file" in names
    assert "project_create_file" in names
    assert "build_run" in names
    assert "parts_install" in names
    assert "manufacturing_generate" in names


def test_both_role_tools_appear_in_both_sets() -> None:
    disc = discovery_tool_names()
    exec_ = execution_tool_names()
    for tool in ("layout_run_drc",):
        assert tool in disc, f"{tool} missing from discovery"
        assert tool in exec_, f"{tool} missing from execution"


def test_discovery_and_execution_cover_all_catalog_tools() -> None:
    disc = discovery_tool_names()
    exec_ = execution_tool_names()
    all_names = disc | exec_
    directory_names = {entry["name"] for entry in mediator.get_tool_directory()}
    assert directory_names <= all_names


# --- tool surfacing ---


def _suggestion_names(suggestions: list[dict]) -> set[str]:
    return {s["name"] for s in suggestions}


def test_suggest_tools_surfaces_build_logs_for_failure_message() -> None:
    suggestions = mediator.suggest_tools(
        message="can you inspect build a13d257908e95383 failure logs?",
        history=[],
        selected_targets=[],
        tool_memory={},
    )
    assert "build_logs_search" in _suggestion_names(suggestions)


def test_suggest_tools_surfaces_parts_for_physical_component_queries() -> None:
    suggestions = mediator.suggest_tools(
        message="search lcsc stm32f4 mcu part",
        history=[],
        selected_targets=[],
        tool_memory={},
    )
    names = _suggestion_names(suggestions)
    assert "parts_search" in names


def test_suggest_tools_surfaces_package_creation_for_local_package_requests() -> None:
    suggestions = mediator.suggest_tools(
        message="create a reusable local package for this lcsc part",
        history=[],
        selected_targets=["default"],
        tool_memory={},
    )
    names = _suggestion_names(suggestions)
    assert "parts_install" in names
    assert "package_create_local" in names


def test_tool_directory_describes_parts_install_package_flow() -> None:
    directory = {entry["name"]: entry for entry in mediator.get_tool_directory()}

    assert "create_package=true" in directory["parts_install"]["tooltip"]
    assert (
        "empty local sub-package scaffold"
        in directory["package_create_local"]["purpose"]
    )


def test_suggest_tools_surfaces_web_search_for_lcsc_id() -> None:
    suggestions = mediator.suggest_tools(
        message="check datasheet for C521608 and review pin functions",
        history=[],
        selected_targets=["default"],
        tool_memory={},
    )
    assert "web_search" in _suggestion_names(suggestions)


def test_suggest_tools_surfaces_bom_tool_for_bom_requests() -> None:
    suggestions = mediator.suggest_tools(
        message="Can you review the BOM and parts list for this target?",
        history=[],
        selected_targets=["default"],
        tool_memory={},
    )
    assert "report_bom" in _suggestion_names(suggestions)


def test_suggest_tools_surfaces_variables_tool_for_parameter_requests() -> None:
    suggestions = mediator.suggest_tools(
        message="Show me the computed parameters and constraints",
        history=[],
        selected_targets=["main"],
        tool_memory={},
    )
    assert "report_variables" in _suggestion_names(suggestions)


def test_suggest_tools_surfaces_module_children_for_hierarchy_requests() -> None:
    suggestions = mediator.suggest_tools(
        message="inspect hierarchy for src/main.ato:App",
        history=[],
        selected_targets=[],
        tool_memory={},
    )
    names = _suggestion_names(suggestions)
    assert "project_module_children" in names or "project_list_modules" in names


def test_suggest_tools_surfaces_manufacturing_generate() -> None:
    suggestions = mediator.suggest_tools(
        message=(
            "generate manufacturing files (gerber + pick and place) for target default"
        ),
        history=[],
        selected_targets=[],
        tool_memory={},
    )
    assert "manufacturing_generate" in _suggestion_names(suggestions)


def test_suggest_tools_surfaces_drc_for_drc_requests() -> None:
    suggestions = mediator.suggest_tools(
        message="run a quick drc check for target default",
        history=[],
        selected_targets=[],
        tool_memory={},
    )
    assert "layout_run_drc" in _suggestion_names(suggestions)


def test_suggest_tools_surfaces_examples_search() -> None:
    suggestions = mediator.suggest_tools(
        message="show an example of i2c module templating in ato",
        history=[],
        selected_targets=[],
        tool_memory={},
    )
    assert "examples_search" in _suggestion_names(suggestions)


def test_suggest_tools_surfaces_package_ato_search() -> None:
    suggestions = mediator.suggest_tools(
        message="search package ato source for regulator enable pattern",
        history=[],
        selected_targets=[],
        tool_memory={},
    )
    assert "package_ato_search" in _suggestion_names(suggestions)


# --- tool memory ---


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
