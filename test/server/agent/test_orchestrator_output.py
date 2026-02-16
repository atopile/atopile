"""Agent module tests moved from colocated runtime modules."""

import pytest

import asyncio
import json
from pathlib import Path

import httpx
from openai import APIStatusError

from atopile.dataclasses import AppContext
from atopile.server.agent.orchestrator import (
    _SYSTEM_PROMPT,
    AgentOrchestrator,
    ToolTrace,
    _build_function_call_outputs_for_model,
    _build_prompt_cache_key,
    _build_session_primer,
    _build_worker_loop_guard_message,
    _extract_retry_after_delay_s,
    _sanitize_tool_output_for_model,
    _tool_call_signature,
    _trim_user_message,
)

def _test_sanitize_tool_output_removes_internal_keys() -> None:
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

def _test_build_function_call_outputs_attaches_datasheet_file() -> None:
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

def _test_build_function_call_outputs_nudges_after_parts_install() -> None:
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

def _test_extract_retry_after_delay_from_message_text() -> None:
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

def _test_responses_create_retries_on_429(monkeypatch) -> None:
    orchestrator = AgentOrchestrator()
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "atopile.server.agent.orchestrator.asyncio.sleep", fake_sleep
    )

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

def _test_responses_create_compacts_and_retries_on_context_overflow() -> None:
    orchestrator = AgentOrchestrator()
    telemetry: dict[str, object] = {"api_retry_count": 0, "compaction_events": []}

    class StubResponses:
        def __init__(self) -> None:
            self.calls = 0
            self.last_previous_response_id: str | None = None
            self.compact_calls = 0

        async def create(self, **kwargs: object) -> dict:
            self.calls += 1
            self.last_previous_response_id = str(kwargs.get("previous_response_id"))
            if self.calls == 1:
                raise _make_api_status_error(
                    status_code=400,
                    body={
                        "error": {
                            "message": "input exceeds context window",
                            "code": "context_length_exceeded",
                        }
                    },
                )
            return {"id": "resp_ok", "output": [], "output_text": "ok"}

        async def compact(self, **_: object) -> dict:
            self.compact_calls += 1
            return {"id": "resp_compact", "output": []}

    class StubClient:
        def __init__(self) -> None:
            self.responses = StubResponses()

    stub_client = StubClient()
    orchestrator._client = stub_client  # type: ignore[assignment]
    result = asyncio.run(
        orchestrator._responses_create(
            {
                "model": "gpt-5-codex",
                "previous_response_id": "resp_old",
                "input": [{"role": "user", "content": "hello"}],
            },
            telemetry=telemetry,
        )
    )

    assert result["id"] == "resp_ok"
    assert stub_client.responses.calls == 2
    assert stub_client.responses.compact_calls == 1
    assert stub_client.responses.last_previous_response_id == "resp_compact"
    events = telemetry.get("compaction_events")
    assert isinstance(events, list)
    assert len(events) == 1

def _test_prompt_cache_key_is_stable_for_same_inputs() -> None:
    key_a = _build_prompt_cache_key(
        project_path=Path("/tmp/demo"),
        tool_defs=[{"name": "project_read_file"}, {"name": "build_run"}],
        skill_state={"selected_skill_ids": ["dev", "domain-layer"]},
        model="gpt-5-codex",
    )
    key_b = _build_prompt_cache_key(
        project_path=Path("/tmp/demo"),
        tool_defs=[{"name": "build_run"}, {"name": "project_read_file"}],
        skill_state={"selected_skill_ids": ["dev", "domain-layer"]},
        model="gpt-5-codex",
    )
    assert key_a == key_b
    assert key_a.startswith("atopile-agent:")

def _test_trim_user_message_preserves_head_and_tail() -> None:
    message = "A" * 120 + "B" * 120
    trimmed = _trim_user_message(message, max_chars=120)
    assert len(trimmed) <= 150
    assert "truncated" in trimmed.lower()
    assert trimmed.startswith("A")
    assert trimmed.endswith("B")

def _test_build_worker_loop_guard_message_detects_repetitive_discovery() -> None:
    traces = [
        ToolTrace(
            name="project_read_file",
            args={"path": "main.ato"},
            ok=True,
            result={"path": "main.ato"},
        )
        for _ in range(6)
    ]
    signatures = [
        _tool_call_signature(
            tool_name="project_read_file", args={"path": "main.ato"}
        )
        for _ in range(6)
    ]

    message = _build_worker_loop_guard_message(
        traces=traces,
        recent_tool_signatures=signatures,
        loops=6,
        guard_hits=0,
        window=8,
        min_discovery=6,
    )

    assert message is not None
    assert "repetitive" in message.lower()

def _test_build_worker_loop_guard_message_ignores_execution_progress() -> None:
    traces = [
        ToolTrace(
            name="project_read_file",
            args={"path": "main.ato"},
            ok=True,
            result={"path": "main.ato"},
        )
        for _ in range(5)
    ] + [
        ToolTrace(
            name="project_edit_file",
            args={"path": "main.ato"},
            ok=True,
            result={"operations_applied": 1},
        )
    ]
    signatures = [
        _tool_call_signature(tool_name=trace.name, args=trace.args)
        for trace in traces
    ]

    message = _build_worker_loop_guard_message(
        traces=traces,
        recent_tool_signatures=signatures,
        loops=6,
        guard_hits=0,
        window=8,
        min_discovery=6,
    )

    assert message is None

def _test_run_worker_turn_stops_repetitive_discovery_loop(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")
    (tmp_path / "main.ato").write_text("module App:\n    pass\n", encoding="utf-8")

    orchestrator = AgentOrchestrator()
    orchestrator.worker_loop_guard_min_discovery = 4
    orchestrator.worker_loop_guard_max_hits = 1
    orchestrator.max_tool_loops = 30

    async def fake_build_context(**_: object) -> str:
        return "Project summary: minimal test context"

    call_counter = {"count": 0}

    async def fake_create_with_context_control(**_: object) -> dict[str, object]:
        call_counter["count"] += 1
        return {
            "id": f"resp_{call_counter['count']}",
            "output": [
                {
                    "type": "function_call",
                    "id": f"fc_{call_counter['count']}",
                    "call_id": f"call_{call_counter['count']}",
                    "name": "project_read_file",
                    "arguments": json.dumps(
                        {"path": "main.ato", "start_line": 1, "max_lines": 40}
                    ),
                }
            ],
        }

    async def fake_execute_tool(**_: object) -> dict[str, object]:
        return {"path": "main.ato", "content": "1:aaaa|module App:"}

    monkeypatch.setattr(orchestrator, "_build_context", fake_build_context)
    monkeypatch.setattr(
        orchestrator,
        "_responses_create_with_context_control",
        fake_create_with_context_control,
    )
    monkeypatch.setattr(
        "atopile.server.agent.orchestrator.tools.execute_tool",
        fake_execute_tool,
    )

    result = asyncio.run(
        orchestrator.run_turn(
            ctx=AppContext(workspace_paths=[tmp_path]),
            project_root=str(tmp_path),
            history=[],
            user_message="Implement the requested feature.",
            selected_targets=["default"],
        )
    )

    assert "repetitive discovery loop" in result.text.lower()
    assert len(result.tool_traces) >= 4
    assert call_counter["count"] >= 4

def _test_run_worker_turn_stops_on_repeated_tool_failures(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")
    (tmp_path / "main.ato").write_text("module App:\n    pass\n", encoding="utf-8")

    orchestrator = AgentOrchestrator()
    orchestrator.worker_failure_streak_limit = 2
    orchestrator.max_tool_loops = 20

    async def fake_build_context(**_: object) -> str:
        return "Project summary: minimal test context"

    call_counter = {"count": 0}

    async def fake_create_with_context_control(**_: object) -> dict[str, object]:
        call_counter["count"] += 1
        return {
            "id": f"resp_{call_counter['count']}",
            "output": [
                {
                    "type": "function_call",
                    "id": f"fc_{call_counter['count']}",
                    "call_id": f"call_{call_counter['count']}",
                    "name": "project_edit_file",
                    "arguments": json.dumps(
                        {
                            "path": "main.ato",
                            "edits": [
                                {
                                    "op": "replace",
                                    "line": "1:aaaa",
                                    "old": "module App:",
                                    "new": "module App:",
                                }
                            ],
                        }
                    ),
                }
            ],
        }

    async def fake_execute_tool(**_: object) -> dict[str, object]:
        raise RuntimeError("hash anchor mismatch")

    monkeypatch.setattr(orchestrator, "_build_context", fake_build_context)
    monkeypatch.setattr(
        orchestrator,
        "_responses_create_with_context_control",
        fake_create_with_context_control,
    )
    monkeypatch.setattr(
        "atopile.server.agent.orchestrator.tools.execute_tool",
        fake_execute_tool,
    )

    result = asyncio.run(
        orchestrator.run_turn(
            ctx=AppContext(workspace_paths=[tmp_path]),
            project_root=str(tmp_path),
            history=[],
            user_message="Apply edit.",
            selected_targets=["default"],
        )
    )

    assert "repeated tool failures" in result.text.lower()
    assert len(result.tool_traces) >= 2

def _test_run_worker_turn_stops_after_no_concrete_progress(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

    orchestrator = AgentOrchestrator()
    orchestrator.worker_no_progress_loop_limit = 3
    orchestrator.worker_loop_guard_min_discovery = 10
    orchestrator.max_tool_loops = 30

    async def fake_build_context(**_: object) -> str:
        return "Project summary: minimal test context"

    call_counter = {"count": 0}

    async def fake_create_with_context_control(**_: object) -> dict[str, object]:
        call_counter["count"] += 1
        return {
            "id": f"resp_{call_counter['count']}",
            "output": [
                {
                    "type": "function_call",
                    "id": f"fc_{call_counter['count']}",
                    "call_id": f"call_{call_counter['count']}",
                    "name": "autolayout_status",
                    "arguments": json.dumps({"job_id": "al-123456789abc"}),
                }
            ],
        }

    async def fake_execute_tool(**_: object) -> dict[str, object]:
        return {
            "job_id": "al-123456789abc",
            "state": "running",
            "candidate_count": 0,
        }

    monkeypatch.setattr(orchestrator, "_build_context", fake_build_context)
    monkeypatch.setattr(
        orchestrator,
        "_responses_create_with_context_control",
        fake_create_with_context_control,
    )
    monkeypatch.setattr(
        "atopile.server.agent.orchestrator.tools.execute_tool",
        fake_execute_tool,
    )

    result = asyncio.run(
        orchestrator.run_turn(
            ctx=AppContext(workspace_paths=[tmp_path]),
            project_root=str(tmp_path),
            history=[],
            user_message="Keep monitoring this job.",
            selected_targets=["default"],
        )
    )

    assert "without concrete progress" in result.text.lower()
    assert len(result.tool_traces) >= 3

class TestOrchestratorOutput:
    test_sanitize_tool_output_removes_internal_keys = staticmethod(
        _test_sanitize_tool_output_removes_internal_keys
    )
    test_build_function_call_outputs_attaches_datasheet_file = staticmethod(
        _test_build_function_call_outputs_attaches_datasheet_file
    )
    test_build_function_call_outputs_nudges_after_parts_install = staticmethod(
        _test_build_function_call_outputs_nudges_after_parts_install
    )
    test_extract_retry_after_delay_from_message_text = staticmethod(
        _test_extract_retry_after_delay_from_message_text
    )
    test_responses_create_retries_on_429 = staticmethod(
        _test_responses_create_retries_on_429
    )
    test_responses_create_compacts_and_retries_on_context_overflow = staticmethod(
        _test_responses_create_compacts_and_retries_on_context_overflow
    )
    test_prompt_cache_key_is_stable_for_same_inputs = staticmethod(
        _test_prompt_cache_key_is_stable_for_same_inputs
    )
    test_trim_user_message_preserves_head_and_tail = staticmethod(
        _test_trim_user_message_preserves_head_and_tail
    )
    test_build_worker_loop_guard_message_detects_repetitive_discovery = (
        staticmethod(
            _test_build_worker_loop_guard_message_detects_repetitive_discovery
        )
    )
    test_build_worker_loop_guard_message_ignores_execution_progress = staticmethod(
        _test_build_worker_loop_guard_message_ignores_execution_progress
    )
    test_run_worker_turn_stops_repetitive_discovery_loop = staticmethod(
        _test_run_worker_turn_stops_repetitive_discovery_loop
    )
    test_run_worker_turn_stops_on_repeated_tool_failures = staticmethod(
        _test_run_worker_turn_stops_on_repeated_tool_failures
    )
    test_run_worker_turn_stops_after_no_concrete_progress = staticmethod(
        _test_run_worker_turn_stops_after_no_concrete_progress
    )
