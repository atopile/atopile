"""Agent module tests moved from colocated runtime modules."""

import pytest

import time
from dataclasses import dataclass

from atopile.server.agent import mediator

@dataclass
class FakeTrace:
    name: str
    ok: bool
    result: dict

def _test_get_tool_directory_includes_core_tools() -> None:
    directory = mediator.get_tool_directory()
    names = {entry["name"] for entry in directory}

    assert "project_read_file" in names
    assert "datasheet_read" in names
    assert "project_create_path" in names
    assert "project_create_file" in names
    assert "project_create_folder" in names
    assert "project_move_path" in names
    assert "project_rename_path" in names
    assert "project_delete_path" in names
    assert "build_logs_search" in names
    assert "design_diagnostics" in names
    assert "manufacturing_generate" in names
    assert "autolayout_run" in names
    assert "autolayout_status" in names
    assert "autolayout_fetch_to_layout" in names
    assert "autolayout_request_screenshot" in names
    assert "layout_run_drc" in names
    assert "autolayout_configure_board_intent" in names
    assert "examples_list" in names
    assert "examples_search" in names
    assert "examples_read_ato" in names
    assert "package_ato_list" in names
    assert "package_ato_search" in names
    assert "package_ato_read" in names

def _test_suggest_tools_prefills_build_logs_from_message() -> None:
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

def _test_tool_memory_view_marks_stale_entries() -> None:
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

def _test_update_tool_memory_summarizes_results() -> None:
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

def _test_suggest_tools_prefers_parts_for_physical_component_queries() -> None:
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

def _test_suggest_tools_prefills_debug_log_filters() -> None:
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

def _test_suggest_tools_prefills_datasheet_read_from_lcsc_id() -> None:
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

def _test_suggest_tools_surfaces_bom_tool_for_bom_requests() -> None:
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

def _test_suggest_tools_surfaces_variables_tool_for_parameter_requests() -> None:
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

def _test_suggest_tools_prefills_module_children_from_entry_point() -> None:
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

def _test_suggest_tools_surfaces_manufacturing_generate_for_generation_intent() -> (
    None
):
    suggestions = mediator.suggest_tools(
        message=(
            "generate manufacturing files (gerber + pick and place) "
            "for target default"
        ),
        history=[],
        selected_targets=[],
        tool_memory={},
    )

    generate = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "manufacturing_generate"
        ),
        None,
    )
    assert generate is not None
    assert generate["prefilled_args"]["target"] == "default"
    assert generate["prefilled_args"]["include_targets"] == ["mfg-data"]

def _test_suggest_tools_surfaces_autolayout_for_routing_intent() -> None:
    suggestions = mediator.suggest_tools(
        message="run deeppcb autoroute for target default in background",
        history=[],
        selected_targets=[],
        tool_memory={},
    )

    autolayout_run = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "autolayout_run"
        ),
        None,
    )
    assert autolayout_run is not None
    assert autolayout_run["prefilled_args"]["job_type"] == "Routing"
    assert autolayout_run["prefilled_args"]["build_target"] == "default"

def _test_suggest_tools_prefills_autolayout_status_from_recent_memory() -> None:
    memory = {
        "autolayout_run": {
            "tool_name": "autolayout_run",
            "summary": "queued",
            "ok": True,
            "updated_at": time.time(),
            "context_id": "al-123456789abc",
        }
    }

    suggestions = mediator.suggest_tools(
        message="check in periodically on autolayout progress",
        history=[],
        selected_targets=[],
        tool_memory=memory,
    )

    status_tool = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "autolayout_status"
        ),
        None,
    )
    assert status_tool is not None
    assert status_tool["prefilled_args"]["job_id"] == "al-123456789abc"
    assert status_tool["prefilled_args"]["wait_seconds"] == 120

def _test_suggest_tools_prefills_layout_run_drc() -> None:
    suggestions = mediator.suggest_tools(
        message="run a quick drc check for target default",
        history=[],
        selected_targets=[],
        tool_memory={},
    )

    drc_tool = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "layout_run_drc"
        ),
        None,
    )
    assert drc_tool is not None
    assert drc_tool["prefilled_args"]["target"] == "default"
    assert drc_tool["prefilled_args"]["max_findings"] == 40

def _test_update_tool_memory_extracts_latest_autolayout_job_id() -> None:
    traces = [
        FakeTrace(
            name="autolayout_status",
            ok=True,
            result={
                "job_id": None,
                "latest_job_id": "al-aaaaaaaaaaaa",
                "jobs": [
                    {"job_id": "al-aaaaaaaaaaaa"},
                    {"job_id": "al-bbbbbbbbbbbb"},
                ],
            },
        )
    ]

    updated = mediator.update_tool_memory({}, traces)
    entry = updated["autolayout_status"]

    assert entry["context_id"] == "al-aaaaaaaaaaaa"
    assert "latest job" in entry["summary"]

def _test_suggest_tools_prefills_autolayout_status_from_status_memory() -> None:
    memory = {
        "autolayout_status": {
            "tool_name": "autolayout_status",
            "summary": "state=running; candidates=0",
            "ok": True,
            "updated_at": time.time(),
            "context_id": "al-feedfacecafe",
        }
    }

    suggestions = mediator.suggest_tools(
        message="check autolayout status again",
        history=[],
        selected_targets=[],
        tool_memory=memory,
    )

    status_tool = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "autolayout_status"
        ),
        None,
    )
    assert status_tool is not None
    assert status_tool["prefilled_args"]["job_id"] == "al-feedfacecafe"

def _test_suggest_tools_surfaces_stackup_config_tool() -> None:
    suggestions = mediator.suggest_tools(
        message="set 4-layer stackup and add a GND ground plane pour",
        history=[],
        selected_targets=["default"],
        tool_memory={},
    )

    config_tool = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "autolayout_configure_board_intent"
        ),
        None,
    )
    assert config_tool is not None
    args = config_tool["prefilled_args"]
    assert args["build_target"] == "default"
    assert args["layer_count"] == 4
    assert args["enable_ground_pours"] is True

def _test_suggest_tools_prefills_examples_search_for_reference_intent() -> None:
    suggestions = mediator.suggest_tools(
        message="show an example of i2c module templating in ato",
        history=[],
        selected_targets=[],
        tool_memory={},
    )

    examples_search = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "examples_search"
        ),
        None,
    )
    assert examples_search is not None
    assert "query" in examples_search["prefilled_args"]

def _test_suggest_tools_prefills_package_ato_search_for_package_source_intent() -> (
    None
):
    suggestions = mediator.suggest_tools(
        message="search package ato source for regulator enable pattern",
        history=[],
        selected_targets=[],
        tool_memory={},
    )

    package_search = next(
        (
            suggestion
            for suggestion in suggestions
            if suggestion["name"] == "package_ato_search"
        ),
        None,
    )
    assert package_search is not None
    assert "query" in package_search["prefilled_args"]

class TestAgentMediator:
    test_get_tool_directory_includes_core_tools = staticmethod(
        _test_get_tool_directory_includes_core_tools
    )
    test_suggest_tools_prefills_build_logs_from_message = staticmethod(
        _test_suggest_tools_prefills_build_logs_from_message
    )
    test_tool_memory_view_marks_stale_entries = staticmethod(
        _test_tool_memory_view_marks_stale_entries
    )
    test_update_tool_memory_summarizes_results = staticmethod(
        _test_update_tool_memory_summarizes_results
    )
    test_suggest_tools_prefers_parts_for_physical_component_queries = staticmethod(
        _test_suggest_tools_prefers_parts_for_physical_component_queries
    )
    test_suggest_tools_prefills_debug_log_filters = staticmethod(
        _test_suggest_tools_prefills_debug_log_filters
    )
    test_suggest_tools_prefills_datasheet_read_from_lcsc_id = staticmethod(
        _test_suggest_tools_prefills_datasheet_read_from_lcsc_id
    )
    test_suggest_tools_surfaces_bom_tool_for_bom_requests = staticmethod(
        _test_suggest_tools_surfaces_bom_tool_for_bom_requests
    )
    test_suggest_tools_surfaces_variables_tool_for_parameter_requests = (
        staticmethod(
            _test_suggest_tools_surfaces_variables_tool_for_parameter_requests
        )
    )
    test_suggest_tools_prefills_module_children_from_entry_point = staticmethod(
        _test_suggest_tools_prefills_module_children_from_entry_point
    )
    (
        test_suggest_tools_surfaces_manufacturing_generate_for_generation_intent
    ) = staticmethod(
        _test_suggest_tools_surfaces_manufacturing_generate_for_generation_intent
    )
    test_suggest_tools_surfaces_autolayout_for_routing_intent = staticmethod(
        _test_suggest_tools_surfaces_autolayout_for_routing_intent
    )
    test_suggest_tools_prefills_autolayout_status_from_recent_memory = staticmethod(
        _test_suggest_tools_prefills_autolayout_status_from_recent_memory
    )
    test_suggest_tools_prefills_layout_run_drc = staticmethod(
        _test_suggest_tools_prefills_layout_run_drc
    )
    test_update_tool_memory_extracts_latest_autolayout_job_id = staticmethod(
        _test_update_tool_memory_extracts_latest_autolayout_job_id
    )
    test_suggest_tools_prefills_autolayout_status_from_status_memory = staticmethod(
        _test_suggest_tools_prefills_autolayout_status_from_status_memory
    )
    test_suggest_tools_surfaces_stackup_config_tool = staticmethod(
        _test_suggest_tools_surfaces_stackup_config_tool
    )
    test_suggest_tools_prefills_examples_search_for_reference_intent = staticmethod(
        _test_suggest_tools_prefills_examples_search_for_reference_intent
    )
    (
        test_suggest_tools_prefills_package_ato_search_for_package_source_intent
    ) = staticmethod(
        _test_suggest_tools_prefills_package_ato_search_for_package_source_intent
    )
