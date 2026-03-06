from __future__ import annotations

import json
from pathlib import Path

from atopile.dataclasses import AppContext
from atopile.server.agent.checklist import Checklist, ChecklistItem
from atopile.server.agent.provider import LLMResponse, TokenUsage, ToolCall
from atopile.server.agent.runner import AgentRunner


class _StubProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def complete(
        self,
        *,
        messages,
        instructions,
        tools,
        skill_state,
        project_path,
        previous_response_id=None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "messages": messages,
                "instructions": instructions,
                "tools": tools,
                "skill_state": dict(skill_state),
                "project_path": str(project_path),
                "previous_response_id": previous_response_id,
            }
        )
        if len(self.calls) == 1:
            return LLMResponse(
                id="resp_tool_call",
                text="",
                tool_calls=[
                    ToolCall(
                        id="call_design_1",
                        name="design_questions",
                        arguments_raw=(
                            '{"context":"Need preferences","questions":['
                            '{"id":"Q1","question":"Pick one","options":["A","B"],'
                            '"default":"A"}]}'
                        ),
                        arguments={
                            "context": "Need preferences",
                            "questions": [
                                {
                                    "id": "Q1",
                                    "question": "Pick one",
                                    "options": ["A", "B"],
                                    "default": "A",
                                }
                            ],
                        },
                    )
                ],
                phase=None,
            )
        return LLMResponse(
            id="resp_closed",
            text="Questions sent.",
            tool_calls=[],
            phase="final_answer",
        )


class _StubRegistry:
    def definitions(self) -> list[dict[str, object]]:
        return [{"type": "function", "name": "design_questions"}]


class TestRunner:
    def test_design_questions_force_end_closes_provider_chain(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_system_prompt",
            lambda **_: ("system prompt", {}),
        )

        async def _fake_initial_user_message(**_: object) -> str:
            return "user message"

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_initial_user_message",
            _fake_initial_user_message,
        )

        provider = _StubProvider()
        runner = AgentRunner(
            config=type(
                "Cfg",
                (),
                {
                    "model": "test-model",
                    "max_tool_loops": 4,
                    "max_turn_seconds": 60,
                    "max_checklist_continuations": 0,
                    "silent_retry_max": 0,
                    "trace_enabled": False,
                    "trace_preview_max_chars": 200,
                    "tool_output_max_chars": 10_000,
                    "context_summary_max_chars": 2_000,
                    "user_message_max_chars": 2_000,
                },
            )(),
            provider=provider,
            registry=_StubRegistry(),
        )

        import asyncio

        result = asyncio.run(
            runner.run_turn(
                ctx=AppContext(workspace_paths=[project_root.parent]),
                project_root=str(project_root),
                history=[],
                user_message="Build a robot controller",
                session_id="session_1",
            )
        )

        assert result.response_id == "resp_closed"
        assert result.text == ""
        assert len(provider.calls) == 2
        assert provider.calls[1]["previous_response_id"] == "resp_tool_call"
        assert provider.calls[1]["tools"] == []
        outputs = provider.calls[1]["messages"]
        assert isinstance(outputs, list)
        assert outputs[0]["type"] == "function_call_output"
        assert outputs[0]["call_id"] == "call_design_1"

    def test_design_questions_marks_questions_checklist_item_done(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

        checklist = Checklist(
            items=[
                ChecklistItem(
                    id="questions",
                    description="Ask the user the remaining design questions",
                    criteria="Questions asked",
                    status="doing",
                )
            ],
            created_at=0,
        )

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_system_prompt",
            lambda **_: ("system prompt", {"checklist": checklist.to_dict()}),
        )

        async def _fake_initial_user_message(**_: object) -> str:
            return "user message"

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_initial_user_message",
            _fake_initial_user_message,
        )

        provider = _StubProvider()
        runner = AgentRunner(
            config=type(
                "Cfg",
                (),
                {
                    "model": "test-model",
                    "max_tool_loops": 4,
                    "max_turn_seconds": 60,
                    "max_checklist_continuations": 0,
                    "silent_retry_max": 0,
                    "trace_enabled": False,
                    "trace_preview_max_chars": 200,
                    "tool_output_max_chars": 10_000,
                    "context_summary_max_chars": 2_000,
                    "user_message_max_chars": 2_000,
                },
            )(),
            provider=provider,
            registry=_StubRegistry(),
        )

        import asyncio

        result = asyncio.run(
            runner.run_turn(
                ctx=AppContext(workspace_paths=[project_root.parent]),
                project_root=str(project_root),
                history=[],
                user_message="Build a robot controller",
                session_id="session_1",
            )
        )

        updated_checklist = result.skill_state["checklist"]["items"]
        assert updated_checklist[0]["id"] == "questions"
        assert updated_checklist[0]["status"] == "done"

    def test_model_commentary_preamble_is_emitted_as_progress(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_system_prompt",
            lambda **_: ("system prompt", {}),
        )

        async def _fake_initial_user_message(**_: object) -> str:
            return "user message"

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_initial_user_message",
            _fake_initial_user_message,
        )

        class _CommentaryProvider:
            def __init__(self) -> None:
                self.calls = 0

            async def complete(
                self,
                *,
                messages,
                instructions,
                tools,
                skill_state,
                project_path,
                previous_response_id=None,
            ) -> LLMResponse:
                self.calls += 1
                if self.calls == 1:
                    return LLMResponse(
                        id="resp_commentary",
                        text=(
                            "I'm going to inspect the project structure, then "
                            "draft the controller architecture."
                        ),
                        tool_calls=[],
                        phase="commentary",
                    )
                return LLMResponse(
                    id="resp_final",
                    text="Done.",
                    tool_calls=[],
                    phase="final_answer",
                )

        progress_events: list[dict[str, object]] = []

        async def _progress(payload: dict[str, object]) -> None:
            progress_events.append(payload)

        runner = AgentRunner(
            config=type(
                "Cfg",
                (),
                {
                    "model": "test-model",
                    "max_tool_loops": 4,
                    "max_turn_seconds": 60,
                    "max_checklist_continuations": 0,
                    "silent_retry_max": 0,
                    "trace_enabled": False,
                    "trace_preview_max_chars": 200,
                    "tool_output_max_chars": 10_000,
                    "context_summary_max_chars": 2_000,
                    "user_message_max_chars": 2_000,
                },
            )(),
            provider=_CommentaryProvider(),
            registry=_StubRegistry(),
        )

        import asyncio

        asyncio.run(
            runner.run_turn(
                ctx=AppContext(workspace_paths=[project_root.parent]),
                project_root=str(project_root),
                history=[],
                user_message="Build a robot controller",
                session_id="session_1",
                progress_callback=_progress,
            )
        )

        assert any(
            event.get("phase") == "thinking"
            and event.get("detail_text")
            == (
                "I'm going to inspect the project structure, then draft the "
                "controller architecture."
            )
            for event in progress_events
        )

    def test_turn_timeout_closes_pending_tool_chain_before_stopping(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_system_prompt",
            lambda **_: ("system prompt", {}),
        )

        async def _fake_initial_user_message(**_: object) -> str:
            return "user message"

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_initial_user_message",
            _fake_initial_user_message,
        )

        monotonic_values = iter([0.0, 0.0, 61.0])

        def _fake_monotonic() -> float:
            try:
                return next(monotonic_values)
            except StopIteration:
                return 61.0

        monkeypatch.setattr(
            "atopile.server.agent.runner.time.monotonic",
            _fake_monotonic,
        )

        class _TimeoutProvider:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            async def complete(
                self,
                *,
                messages,
                instructions,
                tools,
                skill_state,
                project_path,
                previous_response_id=None,
            ) -> LLMResponse:
                self.calls.append(
                    {
                        "messages": messages,
                        "tools": tools,
                        "previous_response_id": previous_response_id,
                    }
                )
                if len(self.calls) == 1:
                    return LLMResponse(
                        id="resp_tool_call",
                        text="",
                        tool_calls=[
                            ToolCall(
                                id="call_timeout_1",
                                name="project_read_file",
                                arguments_raw='{"path":"main.ato"}',
                                arguments={"path": "main.ato"},
                            )
                        ],
                        phase=None,
                    )
                return LLMResponse(
                    id="resp_closed_after_timeout",
                    text="",
                    tool_calls=[],
                    phase="final_answer",
                )

        class _TimeoutRegistry:
            def definitions(self) -> list[dict[str, object]]:
                return [{"type": "function", "name": "project_read_file"}]

            async def execute(self, tool_name, args, project_path, ctx):
                _ = tool_name, project_path, ctx
                return {"ok": True, "path": args["path"], "content": "module main"}

        runner = AgentRunner(
            config=type(
                "Cfg",
                (),
                {
                    "model": "test-model",
                    "max_tool_loops": 4,
                    "max_turn_seconds": 60,
                    "max_checklist_continuations": 0,
                    "silent_retry_max": 0,
                    "trace_enabled": False,
                    "trace_preview_max_chars": 200,
                    "tool_output_max_chars": 10_000,
                    "context_summary_max_chars": 2_000,
                    "user_message_max_chars": 2_000,
                },
            )(),
            provider=_TimeoutProvider(),
            registry=_TimeoutRegistry(),
        )

        import asyncio

        result = asyncio.run(
            runner.run_turn(
                ctx=AppContext(workspace_paths=[project_root.parent]),
                project_root=str(project_root),
                history=[],
                user_message="Build a robot controller",
                session_id="session_1",
            )
        )

        assert result.response_id == "resp_closed_after_timeout"
        assert result.text.startswith(
            "Stopped after exceeding the per-turn time budget"
        )
        assert len(runner._provider.calls) == 2
        assert runner._provider.calls[1]["previous_response_id"] == "resp_tool_call"
        assert runner._provider.calls[1]["tools"] == []
        outputs = runner._provider.calls[1]["messages"]
        assert isinstance(outputs, list)
        assert outputs[0]["type"] == "function_call_output"
        assert outputs[0]["call_id"] == "call_timeout_1"

    def test_stop_request_returns_graceful_handoff_after_tool_outputs(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_system_prompt",
            lambda **_: ("system prompt", {}),
        )

        async def _fake_initial_user_message(**_: object) -> str:
            return "user message"

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_initial_user_message",
            _fake_initial_user_message,
        )

        class _StopProvider:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            async def complete(
                self,
                *,
                messages,
                instructions,
                tools,
                skill_state,
                project_path,
                previous_response_id=None,
            ) -> LLMResponse:
                self.calls.append(
                    {
                        "messages": messages,
                        "tools": tools,
                        "previous_response_id": previous_response_id,
                    }
                )
                if len(self.calls) == 1:
                    return LLMResponse(
                        id="resp_tool_call",
                        text="",
                        tool_calls=[
                            ToolCall(
                                id="call_stop_1",
                                name="project_read_file",
                                arguments_raw='{"path":"main.ato"}',
                                arguments={"path": "main.ato"},
                            )
                        ],
                        phase=None,
                    )
                return LLMResponse(
                    id="resp_stop_handoff",
                    text=(
                        "Stopped cleanly. Completed the current read and can "
                        "resume from wrapper integration."
                    ),
                    tool_calls=[],
                    phase="final_answer",
                )

        class _StopRegistry:
            def definitions(self) -> list[dict[str, object]]:
                return [{"type": "function", "name": "project_read_file"}]

            async def execute(self, tool_name, args, project_path, ctx):
                _ = tool_name, project_path, ctx
                return {"ok": True, "path": args["path"], "content": "module main"}

        provider = _StopProvider()
        runner = AgentRunner(
            config=type(
                "Cfg",
                (),
                {
                    "model": "test-model",
                    "max_tool_loops": 4,
                    "max_turn_seconds": 60,
                    "max_checklist_continuations": 0,
                    "silent_retry_max": 0,
                    "trace_enabled": False,
                    "trace_preview_max_chars": 200,
                    "tool_output_max_chars": 10_000,
                    "context_summary_max_chars": 2_000,
                    "user_message_max_chars": 2_000,
                },
            )(),
            provider=provider,
            registry=_StopRegistry(),
        )

        import asyncio

        result = asyncio.run(
            runner.run_turn(
                ctx=AppContext(workspace_paths=[project_root.parent]),
                project_root=str(project_root),
                history=[],
                user_message="Build a robot controller",
                session_id="session_1",
                stop_requested=lambda: True,
            )
        )

        assert result.text.startswith("Stopped cleanly.")
        assert result.response_id == "resp_stop_handoff"
        assert len(provider.calls) == 2
        outputs = provider.calls[1]["messages"]
        assert isinstance(outputs, list)
        assert outputs[0]["type"] == "function_call_output"
        assert outputs[0]["call_id"] == "call_stop_1"
        assert outputs[1]["role"] == "user"
        assert "stop at the next safe boundary" in outputs[1]["content"]

    def test_interrupt_request_returns_direct_response_after_tool_outputs(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_system_prompt",
            lambda **_: ("system prompt", {}),
        )

        async def _fake_initial_user_message(**_: object) -> str:
            return "user message"

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_initial_user_message",
            _fake_initial_user_message,
        )

        class _InterruptProvider:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            async def complete(
                self,
                *,
                messages,
                instructions,
                tools,
                skill_state,
                project_path,
                previous_response_id=None,
            ) -> LLMResponse:
                self.calls.append(
                    {
                        "messages": messages,
                        "tools": tools,
                        "previous_response_id": previous_response_id,
                    }
                )
                if len(self.calls) == 1:
                    return LLMResponse(
                        id="resp_tool_call",
                        text="",
                        tool_calls=[
                            ToolCall(
                                id="call_interrupt_1",
                                name="project_read_file",
                                arguments_raw='{"path":"main.ato"}',
                                arguments={"path": "main.ato"},
                            )
                        ],
                        phase=None,
                    )
                return LLMResponse(
                    id="resp_interrupt_reply",
                    text=(
                        "The wrapper work was blocked because the MCU and driver "
                        "wrappers still needed pin mapping."
                    ),
                    tool_calls=[],
                    phase="final_answer",
                )

        class _InterruptRegistry:
            def definitions(self) -> list[dict[str, object]]:
                return [{"type": "function", "name": "project_read_file"}]

            async def execute(self, tool_name, args, project_path, ctx):
                _ = tool_name, project_path, ctx
                return {"ok": True, "path": args["path"], "content": "module main"}

        provider = _InterruptProvider()
        runner = AgentRunner(
            config=type(
                "Cfg",
                (),
                {
                    "model": "test-model",
                    "max_tool_loops": 4,
                    "max_turn_seconds": 60,
                    "max_checklist_continuations": 0,
                    "silent_retry_max": 0,
                    "trace_enabled": False,
                    "trace_preview_max_chars": 200,
                    "tool_output_max_chars": 10_000,
                    "context_summary_max_chars": 2_000,
                    "user_message_max_chars": 2_000,
                },
            )(),
            provider=provider,
            registry=_InterruptRegistry(),
        )

        import asyncio

        result = asyncio.run(
            runner.run_turn(
                ctx=AppContext(workspace_paths=[project_root.parent]),
                project_root=str(project_root),
                history=[],
                user_message="Build a robot controller",
                session_id="session_1",
                consume_interrupt_messages=lambda: [
                    "What are you blocked on for the reusable wrappers?"
                ],
                stop_requested=lambda: True,
            )
        )

        assert "blocked because" in result.text
        outputs = provider.calls[1]["messages"]
        assert isinstance(outputs, list)
        assert outputs[0]["type"] == "function_call_output"
        assert outputs[1]["role"] == "user"
        assert "wants a direct reply now" in outputs[1]["content"]

    def test_resumed_turn_restores_persisted_checklist(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_system_prompt",
            lambda **_: ("system prompt", {"mode": "fixed"}),
        )

        async def _fake_initial_user_message(**_: object) -> str:
            return "user message"

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_initial_user_message",
            _fake_initial_user_message,
        )

        class _ChecklistRestoreProvider:
            def __init__(self) -> None:
                self.calls = 0

            async def complete(
                self,
                *,
                messages,
                instructions,
                tools,
                skill_state,
                project_path,
                previous_response_id=None,
            ) -> LLMResponse:
                _ = (
                    messages,
                    instructions,
                    tools,
                    skill_state,
                    project_path,
                    previous_response_id,
                )
                self.calls += 1
                if self.calls == 1:
                    return LLMResponse(
                        id="resp_add",
                        text="",
                        tool_calls=[
                            ToolCall(
                                id="call_add_1",
                                name="checklist_add_items",
                                arguments_raw=json.dumps(
                                    {
                                        "items": [
                                            {
                                                "id": "implement",
                                                "description": "Implement it",
                                                "criteria": "Implemented",
                                            }
                                        ]
                                    }
                                ),
                                arguments={
                                    "items": [
                                        {
                                            "id": "implement",
                                            "description": "Implement it",
                                            "criteria": "Implemented",
                                        }
                                    ]
                                },
                            )
                        ],
                        phase=None,
                    )
                return LLMResponse(
                    id="resp_final",
                    text="Done.",
                    tool_calls=[],
                    phase="final_answer",
                )

        class _ChecklistRegistry:
            def definitions(self) -> list[dict[str, object]]:
                return [{"type": "function", "name": "checklist_add_items"}]

        runner = AgentRunner(
            config=type(
                "Cfg",
                (),
                {
                    "model": "test-model",
                    "max_tool_loops": 4,
                    "max_turn_seconds": 60,
                    "max_checklist_continuations": 0,
                    "silent_retry_max": 0,
                    "trace_enabled": False,
                    "trace_preview_max_chars": 200,
                    "tool_output_max_chars": 10_000,
                    "context_summary_max_chars": 2_000,
                    "user_message_max_chars": 2_000,
                },
            )(),
            provider=_ChecklistRestoreProvider(),
            registry=_ChecklistRegistry(),
        )

        import asyncio

        result = asyncio.run(
            runner.run_turn(
                ctx=AppContext(workspace_paths=[project_root.parent]),
                project_root=str(project_root),
                history=[{"role": "user", "content": "prior"}],
                user_message="continue",
                session_id="session_1",
                prior_skill_state={
                    "checklist": Checklist(
                        items=[
                            ChecklistItem(
                                id="questions",
                                description="Ask questions",
                                criteria="Questions asked",
                                status="done",
                            )
                        ],
                        created_at=0,
                    ).to_dict()
                },
            )
        )

        updated_checklist = result.skill_state["checklist"]["items"]
        assert [item["id"] for item in updated_checklist] == ["questions", "implement"]

    def test_checklist_create_merges_with_existing_checklist(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_system_prompt",
            lambda **_: ("system prompt", {"mode": "fixed"}),
        )

        async def _fake_initial_user_message(**_: object) -> str:
            return "user message"

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_initial_user_message",
            _fake_initial_user_message,
        )

        class _ChecklistMergeProvider:
            def __init__(self) -> None:
                self.calls = 0

            async def complete(
                self,
                *,
                messages,
                instructions,
                tools,
                skill_state,
                project_path,
                previous_response_id=None,
            ) -> LLMResponse:
                _ = (
                    messages,
                    instructions,
                    tools,
                    skill_state,
                    project_path,
                    previous_response_id,
                )
                self.calls += 1
                if self.calls == 1:
                    return LLMResponse(
                        id="resp_create",
                        text="",
                        tool_calls=[
                            ToolCall(
                                id="call_create_1",
                                name="checklist_create",
                                arguments_raw=json.dumps(
                                    {
                                        "items": [
                                            {
                                                "id": "questions",
                                                "description": "Ask questions",
                                                "criteria": "Asked",
                                            },
                                            {
                                                "id": "build",
                                                "description": "Build it",
                                                "criteria": "Built",
                                            },
                                        ]
                                    }
                                ),
                                arguments={
                                    "items": [
                                        {
                                            "id": "questions",
                                            "description": "Ask questions",
                                            "criteria": "Asked",
                                        },
                                        {
                                            "id": "build",
                                            "description": "Build it",
                                            "criteria": "Built",
                                        },
                                    ]
                                },
                            )
                        ],
                        phase=None,
                    )
                return LLMResponse(
                    id="resp_final",
                    text="Done.",
                    tool_calls=[],
                    phase="final_answer",
                )

        class _ChecklistCreateRegistry:
            def definitions(self) -> list[dict[str, object]]:
                return [{"type": "function", "name": "checklist_create"}]

        runner = AgentRunner(
            config=type(
                "Cfg",
                (),
                {
                    "model": "test-model",
                    "max_tool_loops": 4,
                    "max_turn_seconds": 60,
                    "max_checklist_continuations": 0,
                    "silent_retry_max": 0,
                    "trace_enabled": False,
                    "trace_preview_max_chars": 200,
                    "tool_output_max_chars": 10_000,
                    "context_summary_max_chars": 2_000,
                    "user_message_max_chars": 2_000,
                },
            )(),
            provider=_ChecklistMergeProvider(),
            registry=_ChecklistCreateRegistry(),
        )

        import asyncio

        result = asyncio.run(
            runner.run_turn(
                ctx=AppContext(workspace_paths=[project_root.parent]),
                project_root=str(project_root),
                history=[{"role": "user", "content": "prior"}],
                user_message="continue",
                session_id="session_1",
                prior_skill_state={
                    "checklist": Checklist(
                        items=[
                            ChecklistItem(
                                id="questions",
                                description="Ask questions",
                                criteria="Asked",
                                status="done",
                            )
                        ],
                        created_at=0,
                    ).to_dict()
                },
            )
        )

        updated_checklist = result.skill_state["checklist"]["items"]
        assert [item["id"] for item in updated_checklist] == ["questions", "build"]

    def test_runner_emits_model_usage_and_loop_summary_progress(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_system_prompt",
            lambda **_: ("system prompt", {}),
        )

        async def _fake_initial_user_message(**_: object) -> str:
            return "user message"

        monkeypatch.setattr(
            "atopile.server.agent.runner.build_initial_user_message",
            _fake_initial_user_message,
        )

        class _UsageProvider:
            def __init__(self) -> None:
                self.calls = 0

            async def complete(
                self,
                *,
                messages,
                instructions,
                tools,
                skill_state,
                project_path,
                previous_response_id=None,
            ) -> LLMResponse:
                _ = (
                    messages,
                    instructions,
                    tools,
                    skill_state,
                    project_path,
                    previous_response_id,
                )
                self.calls += 1
                if self.calls == 1:
                    return LLMResponse(
                        id="resp_tool",
                        text="",
                        tool_calls=[
                            ToolCall(
                                id="call_read_1",
                                name="project_read_file",
                                arguments_raw='{"path":"main.ato"}',
                                arguments={"path": "main.ato"},
                            )
                        ],
                        usage=TokenUsage(
                            input_tokens=100,
                            output_tokens=25,
                            total_tokens=125,
                            reasoning_tokens=7,
                            cached_input_tokens=80,
                        ),
                    )
                return LLMResponse(
                    id="resp_done",
                    text="Done.",
                    tool_calls=[],
                    phase="final_answer",
                    usage=TokenUsage(
                        input_tokens=50,
                        output_tokens=10,
                        total_tokens=60,
                        reasoning_tokens=3,
                        cached_input_tokens=40,
                    ),
                )

        class _UsageRegistry:
            def definitions(self) -> list[dict[str, object]]:
                return [{"type": "function", "name": "project_read_file"}]

            async def execute(self, tool_name, args, project_path, ctx):
                _ = tool_name, project_path, ctx
                return {"ok": True, "path": args["path"], "content": "module main"}

        progress_events: list[dict[str, object]] = []

        async def _progress(payload: dict[str, object]) -> None:
            progress_events.append(payload)

        runner = AgentRunner(
            config=type(
                "Cfg",
                (),
                {
                    "model": "test-model",
                    "max_tool_loops": 4,
                    "max_turn_seconds": 60,
                    "max_checklist_continuations": 0,
                    "silent_retry_max": 0,
                    "trace_enabled": False,
                    "trace_preview_max_chars": 200,
                    "tool_output_max_chars": 10_000,
                    "context_summary_max_chars": 2_000,
                    "user_message_max_chars": 2_000,
                },
            )(),
            provider=_UsageProvider(),
            registry=_UsageRegistry(),
        )

        import asyncio

        result = asyncio.run(
            runner.run_turn(
                ctx=AppContext(workspace_paths=[project_root.parent]),
                project_root=str(project_root),
                history=[],
                user_message="Build a robot controller",
                session_id="",
                prior_skill_state={
                    "checklist": Checklist(
                        items=[
                            ChecklistItem(
                                id="existing",
                                description="Already tracked",
                                criteria="Tracked",
                                status="done",
                            )
                        ],
                        created_at=0,
                    ).to_dict()
                },
                progress_callback=_progress,
            )
        )

        assert result.context_metrics["input_tokens"] == 150
        assert result.context_metrics["output_tokens"] == 35
        assert result.context_metrics["total_tokens"] == 185
        assert result.context_metrics["reasoning_tokens"] == 10
        assert result.context_metrics["cached_input_tokens"] == 120
        assert result.context_metrics["model_call_count"] == 2

        response_events = [
            event
            for event in progress_events
            if event.get("step_kind") == "model_response_received"
        ]
        assert len(response_events) == 2
        assert response_events[0]["input_tokens"] == 100
        assert response_events[0]["output_tokens"] == 25
        assert response_events[0]["total_tokens"] == 125
        assert response_events[0]["reasoning_tokens"] == 7
        assert response_events[0]["cached_input_tokens"] == 80

        loop_summaries = [
            event
            for event in progress_events
            if event.get("step_kind") == "loop_summary"
        ]
        assert len(loop_summaries) == 1
        assert loop_summaries[0]["loop"] == 1
        assert loop_summaries[0]["tool_count"] == 1
        assert loop_summaries[0]["model_call_count"] == 1
        assert loop_summaries[0]["total_tokens"] == 60
        assert loop_summaries[0]["reasoning_tokens"] == 3
        assert loop_summaries[0]["cached_input_tokens"] == 40
