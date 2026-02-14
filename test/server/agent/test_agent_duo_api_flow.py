from __future__ import annotations

import asyncio
import time
from pathlib import Path

from atopile.dataclasses import AppContext
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
    from_agent: str,
    to_agent: str,
    visibility: str = "internal",
    payload: dict | None = None,
    requires_ack: bool = False,
) -> dict:
    return {
        "message_id": message_id,
        "thread_id": "thread-api-flow",
        "from_agent": from_agent,
        "to_agent": to_agent,
        "kind": kind,
        "summary": summary,
        "payload": payload or {},
        "visibility": visibility,
        "priority": "normal",
        "requires_ack": requires_ack,
        "correlation_id": None,
        "parent_id": None,
        "created_at": time.time(),
    }


def test_background_run_streams_agent_messages_and_completes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "ato.yaml").write_text("builds: {}\n", encoding="utf-8")

    async def _noop_emit(**_: object) -> None:
        return

    async def fake_run_turn(**kwargs):
        callback = kwargs.get("message_callback")
        intent = _peer_message(
            message_id="msg-intent",
            kind="intent_brief",
            summary="Prepared worker brief.",
            from_agent="manager",
            to_agent="worker",
            payload={"objective": "Create a module"},
            requires_ack=True,
        )
        tool_result = _peer_message(
            message_id="msg-tool",
            kind="tool_result",
            summary="Completed tool: project_read_file",
            from_agent="worker",
            to_agent="manager",
            visibility="user_visible",
            payload={"trace": {"name": "project_read_file", "ok": True}},
        )
        final_response = _peer_message(
            message_id="msg-final",
            kind="final_response",
            summary="Prepared final response.",
            from_agent="manager",
            to_agent="user",
            visibility="user_visible",
            payload={"text": "Implemented requested changes."},
        )

        if callable(callback):
            await callback(intent)
            await callback(tool_result)
            await callback(final_response)

        return AgentTurnResult(
            text="Implemented requested changes.",
            tool_traces=[],
            model="manager+worker",
            response_id="resp-api-flow",
            skill_state={},
            context_metrics={},
            agent_messages=[intent, tool_result, final_response],
        )

    monkeypatch.setattr(agent_routes._orchestrator, "run_turn", fake_run_turn)
    monkeypatch.setattr(agent_routes, "_emit_agent_progress", _noop_emit)
    monkeypatch.setattr(agent_routes, "_emit_agent_message", _noop_emit)
    monkeypatch.setattr(agent_routes, "_persist_sessions_state", lambda: None)
    monkeypatch.setattr(
        agent_routes, "_log_session_event", lambda *_args, **_kwargs: None
    )

    with agent_routes._sessions_lock:
        previous_sessions = dict(agent_routes._sessions)
        agent_routes._sessions.clear()
    with agent_routes._runs_lock:
        previous_runs = dict(agent_routes._runs)
        agent_routes._runs.clear()

    async def scenario() -> None:
        ctx = AppContext(workspace_paths=[tmp_path])
        session = await agent_routes.create_session(
            agent_routes.CreateSessionRequest(projectRoot=str(tmp_path)),
            ctx=ctx,
        )
        run = await agent_routes.create_run(
            session_id=session.session_id,
            request=agent_routes.CreateRunRequest(
                message="Please create the module.",
                projectRoot=str(tmp_path),
                selectedTargets=["default"],
            ),
            ctx=ctx,
        )

        for _ in range(200):
            status = await agent_routes.get_run(
                session_id=session.session_id,
                run_id=run.run_id,
            )
            if status.status != "running":
                break
            await asyncio.sleep(0.01)
        else:
            raise AssertionError("Background run did not complete in time")

        status = await agent_routes.get_run(
            session_id=session.session_id,
            run_id=run.run_id,
        )
        assert status.status == "completed"
        assert status.response is not None
        assert status.response.assistant_message == "Implemented requested changes."
        assert len(status.response.agent_messages) == 3

        messages = await agent_routes.get_run_messages(
            session_id=session.session_id,
            run_id=run.run_id,
            agent="manager",
            limit=50,
        )
        assert messages.count == 3
        assert messages.messages[0].kind == "intent_brief"
        assert messages.messages[1].kind == "tool_result"
        assert messages.messages[2].kind == "final_response"

    try:
        asyncio.run(scenario())
    finally:
        _restore_state(previous_sessions, previous_runs)
