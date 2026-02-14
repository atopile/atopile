from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
from openai import APIStatusError

from atopile.server.agent.orchestrator import (
    AgentOrchestrator,
    _build_function_call_outputs_for_model,
    _build_session_primer,
    _extract_retry_after_delay_s,
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


def _make_api_status_error(
    *,
    status_code: int,
    body: dict | None = None,
    headers: dict[str, str] | None = None,
    text: str | None = None,
) -> APIStatusError:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(
        status_code=status_code,
        request=request,
        headers=headers,
        text=text if text is not None else (json.dumps(body) if body else ""),
    )
    return APIStatusError(
        "api status error",
        response=response,
        body=body,
    )


def test_extract_retry_after_delay_from_message_text() -> None:
    exc = _make_api_status_error(
        status_code=429,
        body={
            "error": {
                "message": (
                    "Rate limit reached. Please try again in 578ms. "
                    "Visit dashboard."
                ),
                "code": "rate_limit_exceeded",
            }
        },
    )
    delay_s = _extract_retry_after_delay_s(exc)
    assert delay_s is not None
    assert delay_s == 0.578


def test_responses_create_retries_on_429(monkeypatch) -> None:
    orchestrator = AgentOrchestrator()
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("atopile.server.agent.orchestrator.asyncio.sleep", fake_sleep)

    class StubResponses:
        def __init__(self) -> None:
            self.calls = 0

        async def create(self, **_: object) -> dict:
            self.calls += 1
            if self.calls == 1:
                raise _make_api_status_error(
                    status_code=429,
                    body={
                        "error": {
                            "message": "Please try again in 250ms.",
                            "code": "rate_limit_exceeded",
                        }
                    },
                    headers={"retry-after-ms": "250"},
                )
            return {"id": "resp_ok", "output": [], "output_text": "ok"}

    class StubClient:
        def __init__(self) -> None:
            self.responses = StubResponses()

    stub_client = StubClient()
    orchestrator._client = stub_client  # type: ignore[assignment]

    result = asyncio.run(
        orchestrator._responses_create({"model": "gpt-5-codex", "input": "ping"})
    )
    assert result["id"] == "resp_ok"
    assert stub_client.responses.calls == 2
    assert sleep_calls == [0.25]
