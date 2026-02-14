from __future__ import annotations

import asyncio
import time
from pathlib import Path

from atopile.server.routes import agent as agent_routes


def test_get_session_skills_returns_selected_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    skill_dir = tmp_path / "dev"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        (
            "---\n"
            "name: dev\n"
            'description: "Development workflow"\n'
            "---\n\n"
            "# dev\n\n"
            "## Quick Start\n\n"
            "ato dev test\n"
        ),
        encoding="utf-8",
    )

    session_id = "session-skills-test"
    session = agent_routes.AgentSession(
        session_id=session_id,
        project_root="/tmp/project",
    )
    session.skill_state = {
        "selected_skill_ids": ["dev", "domain-layer"],
        "selected_skills": [
            {"id": "dev", "name": "dev", "score": 10.0, "chars": 120}
        ],
        "reasoning": ["selected=2 of 10 skills"],
        "total_chars": 120,
        "generated_at": time.time(),
    }

    original_dir = agent_routes._orchestrator.skills_dir
    original_ttl = agent_routes._orchestrator.skill_index_ttl_s
    agent_routes._orchestrator.skills_dir = tmp_path
    agent_routes._orchestrator.skill_index_ttl_s = 0
    with agent_routes._sessions_lock:
        agent_routes._sessions[session_id] = session
    try:
        response = asyncio.run(agent_routes.get_session_skills(session_id))
    finally:
        with agent_routes._sessions_lock:
            agent_routes._sessions.pop(session_id, None)
        agent_routes._orchestrator.skills_dir = original_dir
        agent_routes._orchestrator.skill_index_ttl_s = original_ttl

    assert response.session_id == session_id
    assert response.selected_skill_ids == ["dev", "domain-layer"]
    assert response.total_chars == 120
    assert response.loaded_skills_count == 1
