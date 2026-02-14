from __future__ import annotations

import asyncio
import time

from atopile.server.agent.orchestrator import AgentTurnResult
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


def _peer_message(
    *,
    message_id: str,
    kind: str,
    summary: str,
    from_agent: str = "manager",
    to_agent: str = "worker",
    payload: dict | None = None,
    requires_ack: bool = False,
) -> dict:
    return {
        "message_id": message_id,
        "thread_id": "thread-1",
        "from_agent": from_agent,
        "to_agent": to_agent,
        "kind": kind,
        "summary": summary,
        "payload": payload or {},
        "visibility": "internal",
        "priority": "normal",
        "requires_ack": requires_ack,
        "correlation_id": None,
        "parent_id": None,
        "created_at": time.time(),
    }


def test_post_agent_run_message_tracks_intent_snapshot_and_ack() -> None:
    session_id = "session-message-post"
    run_id = "run-message-post"

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
            message="start",
            project_root="/tmp/project",
            status="running",
        )

    try:
        intent_message = _peer_message(
            message_id="msg-intent",
            kind="intent_brief",
            summary="Intent prepared.",
            payload={"objective": "Implement dual-agent workflow"},
            requires_ack=True,
        )
        agent_routes._post_agent_run_message(run_id, intent_message)

        ack_message = _peer_message(
            message_id="msg-ack",
            kind="ack",
            summary="Acknowledged.",
            from_agent="worker",
            to_agent="manager",
            payload={"message_id": "msg-intent"},
        )
        agent_routes._post_agent_run_message(run_id, ack_message)

        with agent_routes._runs_lock:
            run = agent_routes._runs[run_id]
            assert run.intent_snapshot == {"objective": "Implement dual-agent workflow"}
            assert run.pending_acks == set()
            assert len(run.message_log) == 2
    finally:
        _restore_state(previous_sessions, previous_runs)


def test_get_run_messages_returns_messages_and_pending_ack_count() -> None:
    session_id = "session-run-messages"
    run_id = "run-run-messages"

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
            message="start",
            project_root="/tmp/project",
            status="running",
        )

    try:
        agent_routes._post_agent_run_message(
            run_id,
            _peer_message(
                message_id="msg-intent",
                kind="intent_brief",
                summary="Intent prepared.",
                payload={"objective": "Ship feature"},
                requires_ack=True,
            ),
        )

        response = asyncio.run(
            agent_routes.get_run_messages(
                session_id=session_id,
                run_id=run_id,
                agent="manager",
                limit=10,
            )
        )
        assert response.run_id == run_id
        assert response.session_id == session_id
        assert response.count == 1
        assert response.pending_acks == 1
        assert response.messages[0].message_id == "msg-intent"
        assert response.messages[0].kind == "intent_brief"

        follow_up = asyncio.run(
            agent_routes.get_run_messages(
                session_id=session_id,
                run_id=run_id,
                agent="manager",
                limit=10,
            )
        )
        assert follow_up.count == 0
        assert follow_up.messages == []
    finally:
        _restore_state(previous_sessions, previous_runs)


def test_build_send_message_response_includes_agent_messages(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_routes, "_log_session_event", lambda *_args, **_kwargs: None
    )
    session = agent_routes.AgentSession(
        session_id="session-response",
        project_root="/tmp/project",
    )
    result = AgentTurnResult(
        text="Complete.",
        tool_traces=[],
        model="manager+worker",
        response_id="resp_abc",
        skill_state={},
        context_metrics={},
        agent_messages=[
            _peer_message(
                message_id="msg-final",
                kind="final_response",
                summary="Final response prepared.",
                from_agent="manager",
                to_agent="user",
                payload={"text": "Complete."},
            )
        ],
    )

    response = agent_routes._build_send_message_response(
        session=session,
        user_message="Please do it.",
        result=result,
        mode="sync",
        run_id="run-response",
    )

    assert response.agent_messages
    assert response.agent_messages[0].message_id == "msg-final"
    assert response.agent_messages[0].kind == "final_response"
