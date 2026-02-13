from __future__ import annotations

import json
from pathlib import Path

from atopile.server.routes import agent as agent_routes


def test_log_session_event_writes_jsonl(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "agent_sessions.jsonl"
    monkeypatch.setenv("ATOPILE_AGENT_SESSION_LOG_PATH", str(log_path))

    agent_routes._log_session_event(
        "session_created",
        {"session_id": "session-1", "project_root": "/tmp/project"},
    )

    raw = log_path.read_text(encoding="utf-8").strip()
    entry = json.loads(raw)
    assert entry["event"] == "session_created"
    assert entry["session_id"] == "session-1"
    assert entry["project_root"] == "/tmp/project"
    assert "ts" in entry


def test_default_log_path_name(monkeypatch) -> None:
    monkeypatch.delenv("ATOPILE_AGENT_SESSION_LOG_PATH", raising=False)
    path = agent_routes._get_agent_session_log_path()
    assert path.name == "agent_sessions.jsonl"
