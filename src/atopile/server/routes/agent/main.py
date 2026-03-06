"""Agent chat and orchestration routes."""

from __future__ import annotations

import asyncio
import sys
import time
import uuid
from pathlib import Path

import pytest
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

import atopile.server.routes.agent.state as agent_state
from atopile.dataclasses import AppContext
from atopile.server.agent.tools import validate_tool_scope
from atopile.server.domains.deps import get_ctx
from atopile.server.routes.agent import utils as agent_utils

from .models import (
    DETAIL_TEXT_APPLYING_GUIDANCE,
    ERROR_MESSAGE_EMPTY,
    EVENT_RUN_CREATED,
    EVENT_RUN_INTERRUPT_QUEUED,
    EVENT_RUN_STEER_QUEUED,
    EVENT_RUN_STOP_REQUESTED,
    EVENT_SESSION_CREATED,
    EVENT_SESSION_PROJECT_SWITCHED,
    EVENT_TURN_FAILED,
    EVENT_TURN_STARTED,
    PHASE_ERROR,
    PHASE_THINKING,
    RUN_STATUS_RUNNING,
    STATUS_TEXT_STEERING,
    TURN_MODE_BACKGROUND,
    TURN_MODE_SYNC,
    AgentRun,
    AgentSession,
    CancelRunResponse,
    CreateRunRequest,
    CreateRunResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    GetRunResponse,
    InterruptRunRequest,
    InterruptRunResponse,
    SendMessageRequest,
    SendMessageResponse,
    SessionSkillsResponse,
    SteerRunRequest,
    SteerRunResponse,
    active_run_conflict_detail,
    run_not_found_detail,
    session_not_found_detail,
)
from .state import (
    cleanup_finished_runs,
    ensure_session_idle,
    normalize_running_run_state,
    persist_sessions_state,
    release_sync_turn,
    reserve_background_run,
    reserve_sync_turn,
    reset_session_state,
    runs_by_id,
    runs_lock,
    sessions_by_id,
    sessions_lock,
)
from .tools import router as tools_router
from .utils import (
    build_run_trace_callback,
    build_send_message_response,
    emit_agent_progress,
    invalidate_session_response_chain,
    is_chain_integrity_error,
    log_agent_event,
    orchestrator,
    run_turn_in_background,
    run_turn_with_chain_recovery,
)

router = APIRouter(prefix="/api/agent", tags=["agent"])
router.include_router(tools_router)


def _ensure_project_scope(
    session_id: str,
    session: AgentSession,
    project_root: str,
) -> None:
    """Reset the session if the request switches to another project root."""
    if session.project_root == project_root:
        return

    log_agent_event(
        EVENT_SESSION_PROJECT_SWITCHED,
        {
            "session_id": session_id,
            "from_project_root": session.project_root,
            "to_project_root": project_root,
        },
    )
    reset_session_state(session, project_root=project_root)
    persist_sessions_state()


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    ctx: AppContext = Depends(get_ctx),
):
    try:
        validate_tool_scope(request.project_root, ctx)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    session_id = uuid.uuid4().hex
    session = AgentSession(session_id=session_id, project_root=request.project_root)

    with sessions_lock:
        sessions_by_id[session_id] = session
    persist_sessions_state()

    log_agent_event(
        EVENT_SESSION_CREATED,
        {
            "session_id": session_id,
            "project_root": request.project_root,
        },
    )

    return CreateSessionResponse(sessionId=session_id, projectRoot=request.project_root)


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    ctx: AppContext = Depends(get_ctx),
):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail=ERROR_MESSAGE_EMPTY)

    cleanup_finished_runs()
    try:
        validate_tool_scope(request.project_root, ctx)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    with sessions_lock:
        session = sessions_by_id.get(session_id)

    if not session:
        raise HTTPException(
            status_code=404, detail=session_not_found_detail(session_id)
        )

    reservation_token = reserve_sync_turn(session)
    if reservation_token is None:
        active_run = ensure_session_idle(session)
        conflict_run_id = (
            active_run.run_id if active_run else session.active_run_id or ""
        )
        raise HTTPException(
            status_code=409,
            detail=active_run_conflict_detail(conflict_run_id or "sync"),
        )

    _ensure_project_scope(session_id, session, request.project_root)
    session.recent_selected_targets = list(request.selected_targets)

    run_id = uuid.uuid4().hex
    log_agent_event(
        EVENT_TURN_STARTED,
        {
            "session_id": session_id,
            "run_id": run_id,
            "mode": TURN_MODE_SYNC,
            "project_root": request.project_root,
            "selected_targets": list(request.selected_targets),
            "message": request.message,
        },
    )

    async def emit_progress(payload: dict) -> None:
        await emit_agent_progress(
            session_id=session_id,
            project_root=request.project_root,
            run_id=run_id,
            payload=payload,
        )

    trace_callback = build_run_trace_callback(
        session_id=session_id,
        run_id=run_id,
        project_root=request.project_root,
    )

    try:
        try:
            result = await run_turn_with_chain_recovery(
                session=session,
                ctx=ctx,
                project_root=request.project_root,
                history=list(session.history),
                user_message=request.message,
                session_id=session_id,
                selected_targets=request.selected_targets,
                prior_skill_state=session.skill_state,
                tool_memory=session.tool_memory,
                progress_callback=emit_progress,
                trace_callback=trace_callback,
            )
        except Exception as exc:
            if is_chain_integrity_error(str(exc)):
                invalidate_session_response_chain(session)
                persist_sessions_state()
            await emit_progress({"phase": PHASE_ERROR, "error": str(exc)})
            log_agent_event(
                EVENT_TURN_FAILED,
                {
                    "session_id": session_id,
                    "run_id": run_id,
                    "mode": TURN_MODE_SYNC,
                    "project_root": request.project_root,
                    "error": str(exc),
                },
            )
            raise HTTPException(status_code=500, detail=str(exc))

        response = build_send_message_response(
            session=session,
            user_message=request.message,
            steering_messages=[],
            result=result,
            mode=TURN_MODE_SYNC,
            run_id=run_id,
        )
        persist_sessions_state()
        return response
    finally:
        release_sync_turn(session_id, reservation_token)


@router.post("/sessions/{session_id}/runs", response_model=CreateRunResponse)
async def create_run(
    session_id: str,
    request: CreateRunRequest,
    ctx: AppContext = Depends(get_ctx),
):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail=ERROR_MESSAGE_EMPTY)

    cleanup_finished_runs()
    try:
        validate_tool_scope(request.project_root, ctx)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    with sessions_lock:
        session = sessions_by_id.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail=session_not_found_detail(session_id)
        )

    _ensure_project_scope(session_id, session, request.project_root)

    run_id = uuid.uuid4().hex
    run = AgentRun(
        run_id=run_id,
        session_id=session_id,
        message=request.message,
        project_root=request.project_root,
        selected_targets=list(request.selected_targets),
        status=RUN_STATUS_RUNNING,
    )

    with sessions_lock:
        current = sessions_by_id.get(session_id)
    if current is None:
        raise HTTPException(
            status_code=404, detail=session_not_found_detail(session_id)
        )
    if not reserve_background_run(current, run):
        active_run = ensure_session_idle(current)
        conflict_run_id = (
            active_run.run_id if active_run else current.active_run_id or "sync"
        )
        raise HTTPException(
            status_code=409,
            detail=active_run_conflict_detail(conflict_run_id),
        )

    persist_sessions_state()
    log_agent_event(
        EVENT_RUN_CREATED,
        {
            "run_id": run_id,
            "session_id": session_id,
            "mode": TURN_MODE_BACKGROUND,
            "project_root": request.project_root,
            "selected_targets": list(request.selected_targets),
            "message": request.message,
        },
    )

    run.task = asyncio.create_task(
        run_turn_in_background(run_id=run_id, session_id=session_id, ctx=ctx)
    )
    return CreateRunResponse(runId=run_id, status=RUN_STATUS_RUNNING)


@router.get("/sessions/{session_id}/runs/{run_id}", response_model=GetRunResponse)
async def get_run(
    session_id: str,
    run_id: str,
):
    cleanup_finished_runs()

    with runs_lock:
        run = runs_by_id.get(run_id)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=run_not_found_detail(run_id))

    response = (
        SendMessageResponse.model_validate(run.response_payload)
        if run.response_payload
        else None
    )
    return GetRunResponse(
        runId=run.run_id,
        status=run.status,
        response=response,
        error=run.error,
    )


@router.post(
    "/sessions/{session_id}/runs/{run_id}/steer",
    response_model=SteerRunResponse,
)
async def steer_run(
    session_id: str,
    run_id: str,
    request: SteerRunRequest,
):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGE_EMPTY)

    with runs_lock:
        run = runs_by_id.get(run_id)
        if run:
            run = normalize_running_run_state(run)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=run_not_found_detail(run_id))

    if run.status != RUN_STATUS_RUNNING:
        return SteerRunResponse(
            runId=run_id,
            status=run.status,
            queuedMessages=0,
        )

    with runs_lock:
        current = runs_by_id.get(run_id)
        if current is None:
            raise HTTPException(status_code=404, detail=run_not_found_detail(run_id))

        current = normalize_running_run_state(current)
        if current.status != RUN_STATUS_RUNNING:
            return SteerRunResponse(
                runId=run_id,
                status=current.status,
                queuedMessages=0,
            )

        current.steer_messages.append(message)
        current.updated_at = time.time()
        queued_count = len(current.steer_messages)
        run_project_root = current.project_root

    await emit_agent_progress(
        session_id=session_id,
        project_root=run_project_root,
        run_id=run_id,
        payload={
            "phase": PHASE_THINKING,
            "status_text": STATUS_TEXT_STEERING,
            "detail_text": DETAIL_TEXT_APPLYING_GUIDANCE,
        },
    )
    log_agent_event(
        EVENT_RUN_STEER_QUEUED,
        {
            "run_id": run_id,
            "session_id": session_id,
            "project_root": run_project_root,
            "queued_messages": queued_count,
            "message": message,
        },
    )
    return SteerRunResponse(
        runId=run_id,
        status=RUN_STATUS_RUNNING,
        queuedMessages=queued_count,
    )


@router.post(
    "/sessions/{session_id}/runs/{run_id}/cancel",
    response_model=CancelRunResponse,
)
async def cancel_run(
    session_id: str,
    run_id: str,
):
    with runs_lock:
        run = runs_by_id.get(run_id)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=run_not_found_detail(run_id))

    if run.status != RUN_STATUS_RUNNING:
        return CancelRunResponse(runId=run.run_id, status=run.status, error=run.error)
    with runs_lock:
        current = runs_by_id.get(run_id)
        if current:
            current.stop_requested = True
            current.updated_at = time.time()
    persist_sessions_state()

    await emit_agent_progress(
        session_id=session_id,
        project_root=run.project_root,
        run_id=run_id,
        payload={
            "phase": PHASE_THINKING,
            "status_text": "Stopping",
            "detail_text": "Finishing the current step before stopping",
        },
    )
    log_agent_event(
        EVENT_RUN_STOP_REQUESTED,
        {
            "run_id": run_id,
            "session_id": session_id,
            "project_root": run.project_root,
        },
    )

    return CancelRunResponse(
        runId=run_id,
        status=RUN_STATUS_RUNNING,
        error=None,
    )


@router.post(
    "/sessions/{session_id}/runs/{run_id}/interrupt",
    response_model=InterruptRunResponse,
)
async def interrupt_run(
    session_id: str,
    run_id: str,
    request: InterruptRunRequest,
):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail=ERROR_MESSAGE_EMPTY)

    with runs_lock:
        run = runs_by_id.get(run_id)
        if run:
            run = normalize_running_run_state(run)
    if not run or run.session_id != session_id:
        raise HTTPException(status_code=404, detail=run_not_found_detail(run_id))

    if run.status != RUN_STATUS_RUNNING:
        return InterruptRunResponse(
            runId=run_id,
            status=run.status,
            queuedMessages=0,
        )

    with runs_lock:
        current = runs_by_id.get(run_id)
        if current is None:
            raise HTTPException(status_code=404, detail=run_not_found_detail(run_id))

        current = normalize_running_run_state(current)
        if current.status != RUN_STATUS_RUNNING:
            return InterruptRunResponse(
                runId=run_id,
                status=current.status,
                queuedMessages=0,
            )

        current.stop_requested = True
        current.interrupt_messages.append(message)
        current.updated_at = time.time()
        queued_count = len(current.interrupt_messages)
        run_project_root = current.project_root

    persist_sessions_state()

    await emit_agent_progress(
        session_id=session_id,
        project_root=run_project_root,
        run_id=run_id,
        payload={
            "phase": PHASE_THINKING,
            "status_text": "Interrupting",
            "detail_text": "Will respond after the current step",
        },
    )
    log_agent_event(
        EVENT_RUN_INTERRUPT_QUEUED,
        {
            "run_id": run_id,
            "session_id": session_id,
            "project_root": run_project_root,
            "queued_messages": queued_count,
            "message": message,
        },
    )
    return InterruptRunResponse(
        runId=run_id,
        status=RUN_STATUS_RUNNING,
        queuedMessages=queued_count,
    )


@router.get(
    "/sessions/{session_id}/skills",
    response_model=SessionSkillsResponse,
)
async def get_session_skills(
    session_id: str,
):
    with sessions_lock:
        session = sessions_by_id.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail=session_not_found_detail(session_id)
        )

    skills_dir = orchestrator._config.skills_dir
    state = dict(session.skill_state)
    selected_skill_ids = [
        str(value)
        for value in state.get("selected_skill_ids", [])
        if isinstance(value, str)
    ]
    return SessionSkillsResponse(
        sessionId=session.session_id,
        projectRoot=session.project_root,
        skillsDir=str(skills_dir),
        selectedSkillIds=selected_skill_ids,
        selectedSkills=[
            item for item in state.get("selected_skills", []) if isinstance(item, dict)
        ],
        reasoning=[
            str(value) for value in state.get("reasoning", []) if isinstance(value, str)
        ],
        totalChars=int(state.get("total_chars", 0) or 0),
        generatedAt=(
            float(state["generated_at"])
            if isinstance(state.get("generated_at"), (int, float))
            else None
        ),
        loadedSkillsCount=len(selected_skill_ids),
    )


# ----------------------------------------
#                 Tests
# ----------------------------------------


@pytest.fixture(autouse=True)
def _clear_agent_route_state(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys.modules[__name__], "persist_sessions_state", lambda: None)
    monkeypatch.setattr(agent_utils, "persist_sessions_state", lambda: None)
    monkeypatch.setattr(agent_state, "persist_sessions_state", lambda: None)
    monkeypatch.setattr(sys.modules[__name__], "log_agent_event", lambda *_, **__: None)
    monkeypatch.setattr(agent_utils, "log_agent_event", lambda *_, **__: None)
    monkeypatch.setattr(agent_utils.mediator, "suggest_tools", lambda **_: [])
    monkeypatch.setattr(agent_utils.mediator, "get_tool_memory_view", lambda _: [])

    with agent_state.sessions_lock:
        agent_state.sessions_by_id.clear()
    with agent_state.runs_lock:
        agent_state.runs_by_id.clear()
    with agent_state.sync_turns_lock:
        agent_state.sync_turns_by_session.clear()

    yield

    with agent_state.sessions_lock:
        agent_state.sessions_by_id.clear()
    with agent_state.runs_lock:
        agent_state.runs_by_id.clear()
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
    app.include_router(router)
    return app


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAgentRoutes:
    @pytest.mark.anyio
    async def test_invalid_project_root_does_not_reset_session_state(
        self,
        client: AsyncClient,
        project_root: Path,
    ) -> None:
        create = await client.post(
            "/api/agent/sessions",
            json={"projectRoot": str(project_root)},
        )
        assert create.status_code == 200
        session_id = create.json()["sessionId"]

        with agent_state.sessions_lock:
            session = agent_state.sessions_by_id[session_id]
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

        with agent_state.sessions_lock:
            session = agent_state.sessions_by_id[session_id]
            assert session.project_root == str(project_root)
            assert session.history == [{"role": "user", "content": "keep me"}]
            assert session.tool_memory["project_read_file"]["summary"] == "cached"
            assert session.last_response_id == "resp_123"
            assert session.skill_state == {"selected_skill_ids": ["agent"]}

    @pytest.mark.anyio
    async def test_background_run_conflicts_with_reserved_sync_turn(
        self,
        client: AsyncClient,
        project_root: Path,
    ) -> None:
        create = await client.post(
            "/api/agent/sessions",
            json={"projectRoot": str(project_root)},
        )
        assert create.status_code == 200
        session_id = create.json()["sessionId"]

        with agent_state.sessions_lock:
            session = agent_state.sessions_by_id[session_id]
            token = agent_state.reserve_sync_turn(session)
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
        self,
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

        monkeypatch.setattr(orchestrator, "run_turn", fake_run_turn)

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
        self,
        monkeypatch: pytest.MonkeyPatch,
        project_root: Path,
    ) -> None:
        session = AgentSession(
            session_id="session_sync",
            project_root=str(project_root),
            last_response_id="resp_bad",
        )
        with agent_state.sessions_lock:
            agent_state.sessions_by_id[session.session_id] = session

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

        monkeypatch.setattr(orchestrator, "run_turn", fake_run_turn)

        response = await send_message(
            session_id=session.session_id,
            request=SendMessageRequest(
                message="continue",
                projectRoot=str(project_root),
                selectedTargets=[],
            ),
            ctx=AppContext(workspace_paths=[project_root.parent]),
        )
        assert response.assistant_message == "recovered"

        with agent_state.sessions_lock:
            session = agent_state.sessions_by_id[session.session_id]
            assert session.last_response_id == "resp_recovered"

        assert calls == ["resp_bad", None]

    @pytest.mark.anyio
    async def test_background_chain_integrity_error_retries_without_last_response_id(
        self,
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

        with agent_state.sessions_lock:
            agent_state.sessions_by_id[session.session_id] = session
        with agent_state.runs_lock:
            agent_state.runs_by_id[run.run_id] = run

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

        with agent_state.sessions_lock:
            current = agent_state.sessions_by_id[session.session_id]
            assert current.last_response_id == "resp_bg_recovered"

        with agent_state.runs_lock:
            current_run = agent_state.runs_by_id[run.run_id]
            assert current_run.status == "completed"

        assert calls == ["resp_bad", None]

    @pytest.mark.anyio
    async def test_cancel_route_requests_graceful_stop_instead_of_cancelling_task(
        self,
        client: AsyncClient,
        project_root: Path,
    ) -> None:
        session = AgentSession(
            session_id="session_stop",
            project_root=str(project_root),
            active_run_id="run_stop",
        )
        run = AgentRun(
            run_id="run_stop",
            session_id=session.session_id,
            project_root=str(project_root),
            message="work",
        )
        with agent_state.sessions_lock:
            agent_state.sessions_by_id[session.session_id] = session
        with agent_state.runs_lock:
            agent_state.runs_by_id[run.run_id] = run

        response = await client.post(
            f"/api/agent/sessions/{session.session_id}/runs/{run.run_id}/cancel"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == RUN_STATUS_RUNNING
        assert body["error"] is None

        with agent_state.runs_lock:
            updated = agent_state.runs_by_id[run.run_id]
            assert updated.stop_requested is True
            assert updated.status == RUN_STATUS_RUNNING

        with agent_state.sessions_lock:
            updated_session = agent_state.sessions_by_id[session.session_id]
            assert updated_session.active_run_id == run.run_id

    @pytest.mark.anyio
    async def test_interrupt_route_queues_message_and_requests_stop(
        self,
        client: AsyncClient,
        project_root: Path,
    ) -> None:
        session = AgentSession(
            session_id="session_interrupt",
            project_root=str(project_root),
            active_run_id="run_interrupt",
        )
        run = AgentRun(
            run_id="run_interrupt",
            session_id=session.session_id,
            project_root=str(project_root),
            message="work",
        )
        with agent_state.sessions_lock:
            agent_state.sessions_by_id[session.session_id] = session
        with agent_state.runs_lock:
            agent_state.runs_by_id[run.run_id] = run

        response = await client.post(
            f"/api/agent/sessions/{session.session_id}/runs/{run.run_id}/interrupt",
            json={"message": "What are you blocked on?"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == RUN_STATUS_RUNNING
        assert body["queuedMessages"] == 1

        with agent_state.runs_lock:
            updated = agent_state.runs_by_id[run.run_id]
            assert updated.stop_requested is True
            assert updated.interrupt_messages == ["What are you blocked on?"]
