from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import atopile.server.routes.agent.state as agent_state
from atopile.dataclasses import AppContext
from atopile.server.routes.agent import main as agent_routes
from atopile.server.routes.agent import utils as agent_utils
from atopile.server.routes.agent.models import AgentRun


@pytest.fixture(autouse=True)
def _clear_agent_route_state(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(agent_routes, "persist_sessions_state", lambda: None)
    monkeypatch.setattr(agent_utils, "persist_sessions_state", lambda: None)

    with agent_utils.sessions_lock:
        agent_utils.sessions_by_id.clear()
    with agent_utils.runs_lock:
        agent_utils.runs_by_id.clear()
    with agent_state.sync_turns_lock:
        agent_state.sync_turns_by_session.clear()

    yield

    with agent_utils.sessions_lock:
        agent_utils.sessions_by_id.clear()
    with agent_utils.runs_lock:
        agent_utils.runs_by_id.clear()
    with agent_state.sync_turns_lock:
        agent_state.sync_turns_by_session.clear()


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")
    return root


@pytest.fixture
def app(project_root: Path) -> FastAPI:
    app = FastAPI()
    app.state.ctx = AppContext(workspace_paths=[project_root.parent])
    app.include_router(agent_routes.router)
    return app


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_invalid_project_root_does_not_reset_session_state(
    client: AsyncClient,
    project_root: Path,
) -> None:
    create = await client.post(
        "/api/agent/sessions",
        json={"projectRoot": str(project_root)},
    )
    assert create.status_code == 200
    session_id = create.json()["sessionId"]

    with agent_utils.sessions_lock:
        session = agent_utils.sessions_by_id[session_id]
        session.history = [{"role": "user", "content": "keep me"}]
        session.tool_memory = {
            "project_read_file": {
                "tool_name": "project_read_file",
                "summary": "cached",
            }
        }
        session.last_response_id = "resp_123"
        session.skill_state = {"selected_skill_ids": ["agent"]}

    invalid_root = project_root.parent / "outside"
    invalid_root.mkdir()
    response = await client.post(
        f"/api/agent/sessions/{session_id}/messages",
        json={
            "message": "hello",
            "projectRoot": str(invalid_root),
            "selectedTargets": [],
        },
    )
    assert response.status_code == 400

    with agent_utils.sessions_lock:
        session = agent_utils.sessions_by_id[session_id]
        assert session.project_root == str(project_root)
        assert session.history == [{"role": "user", "content": "keep me"}]
        assert session.tool_memory["project_read_file"]["summary"] == "cached"
        assert session.last_response_id == "resp_123"
        assert session.skill_state == {"selected_skill_ids": ["agent"]}


@pytest.mark.anyio
async def test_background_run_conflicts_with_reserved_sync_turn(
    client: AsyncClient,
    project_root: Path,
) -> None:
    create = await client.post(
        "/api/agent/sessions",
        json={"projectRoot": str(project_root)},
    )
    assert create.status_code == 200
    session_id = create.json()["sessionId"]

    with agent_utils.sessions_lock:
        session = agent_utils.sessions_by_id[session_id]
        token = agent_utils.reserve_sync_turn(session)
    assert token is not None

    response = await client.post(
        f"/api/agent/sessions/{session_id}/runs",
        json={
            "message": "do work",
            "projectRoot": str(project_root),
            "selectedTargets": [],
        },
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_second_sync_message_conflicts_while_first_is_running(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    project_root: Path,
) -> None:
    create = await client.post(
        "/api/agent/sessions",
        json={"projectRoot": str(project_root)},
    )
    assert create.status_code == 200
    session_id = create.json()["sessionId"]

    started = asyncio.Event()
    release = asyncio.Event()

    async def fake_run_turn(**_: object):
        started.set()
        await release.wait()

        class Result:
            text = "done"
            tool_traces = []
            model = "test"
            response_id = "resp_sync"
            skill_state = {}
            context_metrics = {}

        return Result()

    monkeypatch.setattr(agent_routes.orchestrator, "run_turn", fake_run_turn)

    first_request = asyncio.create_task(
        client.post(
            f"/api/agent/sessions/{session_id}/messages",
            json={
                "message": "first",
                "projectRoot": str(project_root),
                "selectedTargets": [],
            },
        )
    )
    await started.wait()

    second = await client.post(
        f"/api/agent/sessions/{session_id}/messages",
        json={
            "message": "second",
            "projectRoot": str(project_root),
            "selectedTargets": [],
        },
    )
    assert second.status_code == 409

    release.set()
    first = await first_request
    assert first.status_code == 200


@pytest.mark.anyio
async def test_sync_chain_integrity_error_retries_without_last_response_id(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    project_root: Path,
) -> None:
    create = await client.post(
        "/api/agent/sessions",
        json={"projectRoot": str(project_root)},
    )
    assert create.status_code == 200
    session_id = create.json()["sessionId"]

    with agent_utils.sessions_lock:
        session = agent_utils.sessions_by_id[session_id]
        session.last_response_id = "resp_bad"

    calls: list[object] = []

    async def fake_run_turn(**kwargs: object):
        calls.append(kwargs.get("previous_response_id"))
        if len(calls) == 1:
            raise RuntimeError(
                "Model API request failed (400): No tool output found for "
                "function call call_123."
            )

        class Result:
            text = "recovered"
            tool_traces = []
            model = "test"
            response_id = "resp_recovered"
            skill_state = {}
            context_metrics = {}

        return Result()

    monkeypatch.setattr(agent_routes.orchestrator, "run_turn", fake_run_turn)

    response = await client.post(
        f"/api/agent/sessions/{session_id}/messages",
        json={
            "message": "continue",
            "projectRoot": str(project_root),
            "selectedTargets": [],
        },
    )
    assert response.status_code == 200
    assert response.json()["assistantMessage"] == "recovered"

    with agent_utils.sessions_lock:
        session = agent_utils.sessions_by_id[session_id]
        assert session.last_response_id == "resp_recovered"

    assert calls == ["resp_bad", None]


@pytest.mark.anyio
async def test_background_chain_integrity_error_retries_without_last_response_id(
    monkeypatch: pytest.MonkeyPatch,
    project_root: Path,
) -> None:
    session = agent_utils.AgentSession(
        session_id="session_bg",
        project_root=str(project_root),
        last_response_id="resp_bad",
    )
    run = AgentRun(
        run_id="run_bg",
        session_id=session.session_id,
        message="continue",
        project_root=str(project_root),
        selected_targets=[],
    )

    with agent_utils.sessions_lock:
        agent_utils.sessions_by_id[session.session_id] = session
    with agent_utils.runs_lock:
        agent_utils.runs_by_id[run.run_id] = run

    calls: list[object] = []

    async def fake_run_turn(**kwargs: object):
        calls.append(kwargs.get("previous_response_id"))
        if len(calls) == 1:
            raise RuntimeError(
                "Model API request failed (400): No tool output found for "
                "function call call_123."
            )

        class Result:
            text = "recovered"
            tool_traces = []
            model = "test"
            response_id = "resp_bg_recovered"
            skill_state = {}
            context_metrics = {}

        return Result()

    monkeypatch.setattr(agent_utils.orchestrator, "run_turn", fake_run_turn)
    monkeypatch.setattr(agent_utils, "persist_sessions_state", lambda: None)

    await agent_utils.run_turn_in_background(
        run_id=run.run_id,
        session_id=session.session_id,
        ctx=AppContext(workspace_paths=[project_root.parent]),
    )

    with agent_utils.sessions_lock:
        current = agent_utils.sessions_by_id[session.session_id]
        assert current.last_response_id == "resp_bg_recovered"

    with agent_utils.runs_lock:
        current_run = agent_utils.runs_by_id[run.run_id]
        assert current_run.status == "completed"

    assert calls == ["resp_bad", None]
