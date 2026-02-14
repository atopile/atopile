from __future__ import annotations

import asyncio

from atopile.server.routes import agent as agent_routes


def _restore_state(
    previous_sessions: dict[str, agent_routes.AgentSession],
    previous_runs: dict[str, agent_routes.AgentRun],
) -> None:
    with agent_routes._sessions_lock:
        agent_routes._sessions.clear()
        agent_routes._sessions.update(previous_sessions)
    with agent_routes._runs_lock:
        agent_routes._runs.clear()
        agent_routes._runs.update(previous_runs)


def test_steer_run_queues_message_for_active_run(monkeypatch) -> None:
    session_id = "session-steer-active"
    run_id = "run-steer-active"

    async def _noop_emit(**_: object) -> None:
        return

    monkeypatch.setattr(agent_routes, "_emit_agent_progress", _noop_emit)
    monkeypatch.setattr(
        agent_routes, "_log_session_event", lambda *_args, **_kwargs: None
    )

    with agent_routes._sessions_lock:
        previous_sessions = dict(agent_routes._sessions)
        agent_routes._sessions.clear()
        agent_routes._sessions[session_id] = agent_routes.AgentSession(
            session_id=session_id,
            project_root="/tmp/project",
        )
    with agent_routes._runs_lock:
        previous_runs = dict(agent_routes._runs)
        agent_routes._runs.clear()
        agent_routes._runs[run_id] = agent_routes.AgentRun(
            run_id=run_id,
            session_id=session_id,
            message="initial",
            project_root="/tmp/project",
            status="running",
        )

    try:
        response = asyncio.run(
            agent_routes.steer_run(
                session_id=session_id,
                run_id=run_id,
                request=agent_routes.SteerRunRequest(message="Prefer minimal edits."),
            )
        )
        assert response.status == "running"
        assert response.queued_messages == 1
        with agent_routes._runs_lock:
            queued = list(agent_routes._runs[run_id].steer_messages)
        assert queued == ["Prefer minimal edits."]
    finally:
        _restore_state(previous_sessions, previous_runs)


def test_steer_run_returns_non_running_status(monkeypatch) -> None:
    session_id = "session-steer-complete"
    run_id = "run-steer-complete"

    monkeypatch.setattr(
        agent_routes, "_log_session_event", lambda *_args, **_kwargs: None
    )

    with agent_routes._sessions_lock:
        previous_sessions = dict(agent_routes._sessions)
        agent_routes._sessions.clear()
        agent_routes._sessions[session_id] = agent_routes.AgentSession(
            session_id=session_id,
            project_root="/tmp/project",
        )
    with agent_routes._runs_lock:
        previous_runs = dict(agent_routes._runs)
        agent_routes._runs.clear()
        agent_routes._runs[run_id] = agent_routes.AgentRun(
            run_id=run_id,
            session_id=session_id,
            message="initial",
            project_root="/tmp/project",
            status="completed",
        )

    try:
        response = asyncio.run(
            agent_routes.steer_run(
                session_id=session_id,
                run_id=run_id,
                request=agent_routes.SteerRunRequest(message="Update priority."),
            )
        )
        assert response.status == "completed"
        assert response.queued_messages == 0
        with agent_routes._runs_lock:
            queued = list(agent_routes._runs[run_id].steer_messages)
        assert queued == []
    finally:
        _restore_state(previous_sessions, previous_runs)


def test_background_run_consumes_queued_steering_messages(monkeypatch) -> None:
    session_id = "session-steer-consume"
    run_id = "run-steer-consume"
    consumed: dict[str, list[str]] = {"messages": []}

    class _FakeResult:
        text = "done"
        tool_traces: list[object] = []
        model = "test-model"
        response_id = "resp-test"
        skill_state: dict[str, object] = {}
        context_metrics: dict[str, object] = {}

    async def _fake_run_turn(**kwargs):
        callback = kwargs.get("consume_steering_messages")
        if callable(callback):
            consumed["messages"] = callback()
        return _FakeResult()

    async def _noop_emit(**_: object) -> None:
        return

    monkeypatch.setattr(agent_routes._orchestrator, "run_turn", _fake_run_turn)
    monkeypatch.setattr(agent_routes, "_emit_agent_progress", _noop_emit)
    monkeypatch.setattr(agent_routes, "_persist_sessions_state", lambda: None)
    monkeypatch.setattr(
        agent_routes, "_log_session_event", lambda *_args, **_kwargs: None
    )

    with agent_routes._sessions_lock:
        previous_sessions = dict(agent_routes._sessions)
        agent_routes._sessions.clear()
        agent_routes._sessions[session_id] = agent_routes.AgentSession(
            session_id=session_id,
            project_root="/tmp/project",
            active_run_id=run_id,
        )
    with agent_routes._runs_lock:
        previous_runs = dict(agent_routes._runs)
        agent_routes._runs.clear()
        agent_routes._runs[run_id] = agent_routes.AgentRun(
            run_id=run_id,
            session_id=session_id,
            message="initial",
            project_root="/tmp/project",
            status="running",
            steer_messages=["Keep changes small.", "Avoid build reruns."],
        )

    try:
        asyncio.run(
            agent_routes._run_turn_in_background(
                run_id=run_id,
                session_id=session_id,
                ctx=None,  # type: ignore[arg-type]
            )
        )
        assert consumed["messages"] == ["Keep changes small.", "Avoid build reruns."]
        with agent_routes._runs_lock:
            run = agent_routes._runs[run_id]
            assert run.status == "completed"
            assert run.steer_messages == []
    finally:
        _restore_state(previous_sessions, previous_runs)
