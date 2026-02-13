from __future__ import annotations

from pathlib import Path

from atopile.server.agent.orchestrator import (
    _build_function_call_outputs_for_model,
    _build_session_primer,
    _sanitize_tool_output_for_model,
)


def test_sanitize_tool_output_removes_internal_keys() -> None:
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


def test_build_session_primer_contains_core_orientation() -> None:
    primer = _build_session_primer(
        project_root=Path("/tmp/demo-project"),
        selected_targets=["main.ato"],
    )

    assert "Session primer (one-time orientation):" in primer
    assert "project_root: /tmp/demo-project" in primer
    assert "selected_targets: main.ato" in primer
    assert "project_edit_file anchors (LINE:HASH)" in primer
    assert "parts_search/parts_install" in primer
    assert "stdlib_list and stdlib_get_item" in primer
    assert "report_bom" in primer
    assert "report_variables" in primer
    assert "manufacturing_generate" in primer


def test_build_function_call_outputs_attaches_datasheet_file() -> None:
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


def test_build_function_call_outputs_nudges_after_parts_install() -> None:
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
