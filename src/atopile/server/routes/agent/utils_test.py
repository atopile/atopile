from __future__ import annotations

import sqlite3

from atopile.server.routes.agent import utils as agent_utils


class TestAgentLogging:
    def test_log_agent_event_persists_structured_telemetry_fields(
        self, monkeypatch, tmp_path
    ) -> None:
        db_path = tmp_path / "agent_logs.db"

        monkeypatch.setattr("atopile.model.sqlite.AGENT_LOGS_DB", db_path)
        monkeypatch.setattr(agent_utils, "_agent_logs_db_initialized", False)

        agent_utils.log_agent_event(
            "run_progress",
            {
                "session_id": "session_1",
                "run_id": "run_1",
                "project_root": "/tmp/project",
                "phase": "thinking",
                "step_kind": "model_response_received",
                "loop": 3,
                "tool_index": 1,
                "tool_count": 2,
                "call_id": "call_123",
                "item_id": "pkg-mcu",
                "model": "gpt-5.4",
                "response_id": "resp_123",
                "previous_response_id": "resp_122",
                "input_tokens": 1000,
                "output_tokens": 250,
                "total_tokens": 1250,
                "reasoning_tokens": 200,
                "cached_input_tokens": 800,
                "duration_ms": 3210,
                "status_text": "Model response received",
                "detail_text": "2 tool call(s), phase=unspecified",
            },
        )

        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT event, phase, step_kind, loop, tool_index, tool_count, call_id,
                       item_id, model, response_id, previous_response_id,
                       input_tokens, output_tokens, total_tokens,
                       reasoning_tokens, cached_input_tokens, duration_ms
                FROM agent_events
                """
            ).fetchone()

        assert row == (
            "run_progress",
            "thinking",
            "model_response_received",
            3,
            1,
            2,
            "call_123",
            "pkg-mcu",
            "gpt-5.4",
            "resp_123",
            "resp_122",
            1000,
            250,
            1250,
            200,
            800,
            3210,
        )
