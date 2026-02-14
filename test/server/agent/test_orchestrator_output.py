from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
from openai import APIStatusError

from atopile.dataclasses import AppContext
from atopile.server.agent.orchestrator import (
    AgentOrchestrator,
    AgentTurnResult,
    _SYSTEM_PROMPT,
    _MANAGER_PLANNER_PROMPT,
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


def test_prompts_enforce_abstraction_first_hardware_authoring() -> None:
    assert "abstraction-first structure" in _SYSTEM_PROMPT
    assert "generic passives by default" in _SYSTEM_PROMPT
    assert "Resistor" in _SYSTEM_PROMPT
    assert "Capacitor" in _SYSTEM_PROMPT
    assert "manual netlist" in _SYSTEM_PROMPT
    assert "place critical connectors/components manually" in _SYSTEM_PROMPT
    assert "awaiting_selection" in _SYSTEM_PROMPT
    assert "completed" in _SYSTEM_PROMPT
    assert "module/interface-oriented architecture" in _MANAGER_PLANNER_PROMPT


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
                    "Rate limit reached. Please try again in 578ms. Visit dashboard."
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


def test_responses_create_compacts_and_retries_on_context_overflow() -> None:
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


def test_prompt_cache_key_is_stable_for_same_inputs() -> None:
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


def test_trim_user_message_preserves_head_and_tail() -> None:
    message = "A" * 120 + "B" * 120
    trimmed = _trim_user_message(message, max_chars=120)
    assert len(trimmed) <= 150
    assert "truncated" in trimmed.lower()
    assert trimmed.startswith("A")
    assert trimmed.endswith("B")


def test_build_worker_loop_guard_message_detects_repetitive_discovery() -> None:
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
        _tool_call_signature(tool_name="project_read_file", args={"path": "main.ato"})
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


def test_build_worker_loop_guard_message_ignores_execution_progress() -> None:
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
        _tool_call_signature(tool_name=trace.name, args=trace.args) for trace in traces
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


def test_run_turn_duo_mode_emits_agent_messages(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

    orchestrator = AgentOrchestrator()
    orchestrator.enable_duo_agents = True
    orchestrator.manager_refine_rounds = 0

    async def fake_manager_build_plan(**_: object) -> dict[str, object]:
        return {
            "intent_summary": "Implement dual-agent flow",
            "objective": "Ship the requested implementation",
            "constraints": ["keep scope tight"],
            "acceptance_criteria": ["messages emitted", "final response produced"],
            "worker_brief": "Implement the feature and summarize results.",
            "checkpoints": ["done"],
        }

    async def fake_worker_turn(**_: object) -> AgentTurnResult:
        return AgentTurnResult(
            text="Worker completed implementation.",
            tool_traces=[],
            model="worker-model",
            response_id="resp_worker",
            skill_state={},
            context_metrics={},
        )

    async def fake_manager_review_result(**_: object) -> dict[str, str]:
        return {
            "decision": "accept",
            "refinement_brief": "",
            "final_response": "Manager-approved final response.",
            "completion_summary": "Accepted output.",
        }

    monkeypatch.setattr(orchestrator, "_manager_build_plan", fake_manager_build_plan)
    monkeypatch.setattr(orchestrator, "_run_worker_turn", fake_worker_turn)
    monkeypatch.setattr(
        orchestrator,
        "_manager_review_result",
        fake_manager_review_result,
    )

    emitted: list[dict[str, object]] = []

    async def collect_message(message: dict[str, object]) -> None:
        emitted.append(message)

    result = asyncio.run(
        orchestrator.run_turn(
            ctx=AppContext(workspace_paths=[tmp_path]),
            project_root=str(tmp_path),
            history=[],
            user_message="Please implement the dual-agent protocol.",
            selected_targets=["default"],
            message_callback=collect_message,
        )
    )

    assert result.text == "Manager-approved final response."
    assert result.agent_messages
    assert emitted == result.agent_messages
    assert any(message.get("kind") == "intent_brief" for message in emitted)
    assert any(message.get("kind") == "result_bundle" for message in emitted)
    assert any(message.get("kind") == "final_response" for message in emitted)


def test_run_turn_duo_mode_manager_direct_response_skips_worker(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

    orchestrator = AgentOrchestrator()
    orchestrator.enable_duo_agents = True

    async def fake_manager_build_plan(**_: object) -> dict[str, object]:
        return {
            "execution_mode": "manager_response",
            "delegation_reason": "Question can be answered without tools.",
            "manager_response": "Here is the quick answer without engineering handoff.",
            "intent_summary": "Provide direct answer",
            "objective": "Answer user question",
            "constraints": [],
            "acceptance_criteria": [],
            "worker_brief": "",
            "checkpoints": [],
        }

    async def fail_worker_turn(**_: object) -> AgentTurnResult:
        raise AssertionError("worker should not be called for manager direct response")

    monkeypatch.setattr(orchestrator, "_manager_build_plan", fake_manager_build_plan)
    monkeypatch.setattr(orchestrator, "_run_worker_turn", fail_worker_turn)

    emitted: list[dict[str, object]] = []

    async def collect_message(message: dict[str, object]) -> None:
        emitted.append(message)

    result = asyncio.run(
        orchestrator.run_turn(
            ctx=AppContext(workspace_paths=[tmp_path]),
            project_root=str(tmp_path),
            history=[],
            user_message="Can you summarize what changed?",
            selected_targets=["default"],
            message_callback=collect_message,
        )
    )

    assert result.text == "Here is the quick answer without engineering handoff."
    assert result.tool_traces == []
    assert result.model == orchestrator.manager_model
    assert any(message.get("kind") == "decision" for message in emitted)
    assert any(message.get("kind") == "final_response" for message in emitted)
    assert not any(message.get("kind") == "intent_brief" for message in emitted)


def test_run_turn_duo_mode_reduces_worker_status_noise(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

    orchestrator = AgentOrchestrator()
    orchestrator.enable_duo_agents = True
    orchestrator.manager_refine_rounds = 0

    async def fake_manager_build_plan(**_: object) -> dict[str, object]:
        return {
            "execution_mode": "delegate_worker",
            "delegation_reason": "Needs project work.",
            "manager_response": "",
            "intent_summary": "Implement requested change",
            "objective": "Apply implementation update",
            "constraints": [],
            "acceptance_criteria": ["deliver final response"],
            "worker_brief": "Implement update and report result.",
            "checkpoints": [],
        }

    async def fake_worker_turn(**kwargs: object) -> AgentTurnResult:
        progress_callback = kwargs.get("progress_callback")
        if callable(progress_callback):
            await progress_callback(
                {
                    "phase": "thinking",
                    "status_text": "Planning",
                    "detail_text": "Preparing execution plan",
                }
            )
            await progress_callback(
                {
                    "phase": "thinking",
                    "status_text": "Reviewing tool results",
                    "detail_text": "Choosing next step",
                }
            )
            await progress_callback(
                {
                    "phase": "tool_start",
                    "name": "parts_search",
                    "call_id": "call-1",
                    "args": {"query": "stm32"},
                }
            )
            await progress_callback(
                {
                    "phase": "tool_end",
                    "call_id": "call-1",
                    "trace": {"name": "parts_search", "ok": True, "result": {}},
                }
            )
            await progress_callback(
                {
                    "phase": "tool_start",
                    "name": "autolayout_run",
                    "call_id": "call-2",
                    "args": {"job_type": "Routing"},
                }
            )
            await progress_callback(
                {
                    "phase": "tool_end",
                    "call_id": "call-2",
                    "trace": {"name": "autolayout_run", "ok": True, "result": {}},
                }
            )
        return AgentTurnResult(
            text="Worker completed requested update.",
            tool_traces=[],
            model="worker-model",
            response_id="resp_worker",
            skill_state={},
            context_metrics={},
        )

    async def fake_manager_review_result(**_: object) -> dict[str, str]:
        return {
            "decision": "accept",
            "refinement_brief": "",
            "final_response": "Completed.",
            "completion_summary": "done",
        }

    monkeypatch.setattr(orchestrator, "_manager_build_plan", fake_manager_build_plan)
    monkeypatch.setattr(orchestrator, "_run_worker_turn", fake_worker_turn)
    monkeypatch.setattr(
        orchestrator, "_manager_review_result", fake_manager_review_result
    )

    emitted: list[dict[str, object]] = []

    async def collect_message(message: dict[str, object]) -> None:
        emitted.append(message)

    asyncio.run(
        orchestrator.run_turn(
            ctx=AppContext(workspace_paths=[tmp_path]),
            project_root=str(tmp_path),
            history=[],
            user_message="Do work quietly but keep me informed on big steps.",
            selected_targets=["default"],
            message_callback=collect_message,
        )
    )

    assert any(
        message.get("kind") == "tool_intent"
        and "autolayout_run" in str(message.get("summary", ""))
        for message in emitted
    )
    assert not any(
        message.get("kind") == "tool_intent"
        and "parts_search" in str(message.get("summary", ""))
        for message in emitted
    )
    assert any(
        message.get("kind") == "tool_result"
        and "autolayout_run" in str(message.get("summary", ""))
        for message in emitted
    )
    assert not any(
        message.get("kind") == "tool_result"
        and "parts_search" in str(message.get("summary", ""))
        for message in emitted
    )
    assert not any(
        message.get("kind") == "plan_update"
        and str(message.get("summary", "")).strip().lower() == "reviewing tool results"
        for message in emitted
    )


def test_run_worker_turn_stops_repetitive_discovery_loop(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")
    (tmp_path / "main.ato").write_text("module App:\n    pass\n", encoding="utf-8")

    orchestrator = AgentOrchestrator()
    orchestrator.enable_duo_agents = False
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
