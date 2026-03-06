from __future__ import annotations

import pytest

from atopile.server.agent.activity_summary import ActivitySummarizer
from atopile.server.agent.config import AgentConfig
from atopile.server.routes.agent import utils as agent_utils


class TestActivitySummary:
    @pytest.mark.anyio
    async def test_activity_summarizer_describes_local_package_install(self) -> None:
        summarizer = ActivitySummarizer(
            AgentConfig(activity_summary_enabled=True, api_key=None)
        )

        summary = await summarizer.summarize(
            session_id="s1",
            run_id="r1",
            project_root="/tmp/project",
            payload={
                "phase": "tool_start",
                "name": "parts_install",
                "args": {"lcsc_id": "C12345", "create_package": True},
            },
        )

        assert summary is not None
        assert "local package" in summary.lower()

    @pytest.mark.anyio
    async def test_activity_summarizer_uses_model_rewrite_when_available(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        summarizer = ActivitySummarizer(
            AgentConfig(
                activity_summary_enabled=True,
                api_key="test-key",
                activity_summary_min_interval_s=0.0,
            )
        )

        async def fake_rewrite_with_model(**_: object) -> str:
            return "Editing the STM32 wrapper and tightening power constraints"

        monkeypatch.setattr(summarizer, "_rewrite_with_model", fake_rewrite_with_model)

        summary = await summarizer.summarize(
            session_id="s1",
            run_id="r1",
            project_root="/tmp/project",
            payload={
                "phase": "tool_start",
                "name": "project_edit_file",
                "args": {"path": "packages/stm32/stm32.ato"},
            },
        )

        assert summary == "Editing the STM32 wrapper and tightening power constraints"

    @pytest.mark.anyio
    async def test_emit_agent_progress_attaches_activity_summary(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        emitted: list[tuple[str, dict]] = []

        class _FakeBus:
            async def emit(self, event_type: str, payload: dict) -> None:
                emitted.append((event_type, payload))

        async def fake_summarize(**_: object) -> str:
            return "Running a build to validate changes"

        monkeypatch.setattr(agent_utils, "get_event_bus", lambda: _FakeBus())
        monkeypatch.setattr(
            agent_utils.activity_summarizer, "summarize", fake_summarize
        )

        await agent_utils.emit_agent_progress(
            session_id="session-1",
            project_root="/tmp/project",
            run_id="run-1",
            payload={"phase": "tool_start", "name": "build_run", "args": {}},
        )

        assert emitted == [
            (
                "agent_progress",
                {
                    "session_id": "session-1",
                    "project_root": "/tmp/project",
                    "run_id": "run-1",
                    "phase": "tool_start",
                    "name": "build_run",
                    "args": {},
                    "activity_summary": "Running a build to validate changes",
                },
            )
        ]
