from __future__ import annotations

import json
from pathlib import Path

from atopile.server.routes import agent as agent_routes


def test_default_state_path_name(monkeypatch) -> None:
    monkeypatch.delenv("ATOPILE_AGENT_SESSION_STATE_PATH", raising=False)
    path = agent_routes._get_agent_session_state_path()
    assert path.name == "agent_sessions_state.json"


def test_persist_and_reload_sessions_state(tmp_path: Path, monkeypatch) -> None:
    state_path = tmp_path / "agent_sessions_state.json"
    monkeypatch.setenv("ATOPILE_AGENT_SESSION_STATE_PATH", str(state_path))

    with agent_routes._sessions_lock:
        previous_sessions = dict(agent_routes._sessions)
        agent_routes._sessions.clear()
        session = agent_routes.AgentSession(
            session_id="session-resume-test",
            project_root="/tmp/project",
        )
        session.history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        session.tool_memory = {
            "project_read_file": {
                "summary": "last read",
                "ok": True,
            }
        }
        session.recent_selected_targets = ["default"]
        session.last_response_id = "resp_123"
        session.conversation_id = "conv_456"
        session.skill_state = {"selected_skill_ids": ["dev"]}
        agent_routes._sessions[session.session_id] = session

    try:
        agent_routes._persist_sessions_state()

        with agent_routes._sessions_lock:
            agent_routes._sessions.clear()

        agent_routes._load_sessions_state()

        with agent_routes._sessions_lock:
            restored = agent_routes._sessions.get("session-resume-test")
        assert restored is not None
        assert restored.project_root == "/tmp/project"
        assert restored.history[-1]["content"] == "hi"
        assert "project_read_file" in restored.tool_memory
        assert restored.last_response_id == "resp_123"
        assert restored.conversation_id == "conv_456"
        assert restored.skill_state.get("selected_skill_ids") == ["dev"]
        assert restored.active_run_id is None
    finally:
        with agent_routes._sessions_lock:
            agent_routes._sessions.clear()
            agent_routes._sessions.update(previous_sessions)


def test_load_session_state_skips_invalid_entries(tmp_path: Path, monkeypatch) -> None:
    state_path = tmp_path / "agent_sessions_state.json"
    monkeypatch.setenv("ATOPILE_AGENT_SESSION_STATE_PATH", str(state_path))
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sessions": [
                    {"session_id": "ok", "project_root": "/tmp/project"},
                    {"session_id": 123, "project_root": "/tmp/bad"},
                    "bad-entry",
                ],
            }
        ),
        encoding="utf-8",
    )

    with agent_routes._sessions_lock:
        previous_sessions = dict(agent_routes._sessions)
        agent_routes._sessions.clear()

    try:
        agent_routes._load_sessions_state()
        with agent_routes._sessions_lock:
            assert set(agent_routes._sessions.keys()) == {"ok"}
    finally:
        with agent_routes._sessions_lock:
            agent_routes._sessions.clear()
            agent_routes._sessions.update(previous_sessions)
