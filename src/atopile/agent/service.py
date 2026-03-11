"""Rewrite-native agent service wired through RPC instead of HTTP routes."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable

from atopile.agent.tools import validate_tool_scope
from atopile.dataclasses import AppContext

from . import service_utils, tooling
from .api_models import (
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
    AgentRun,
    AgentServiceError,
    AgentSession,
    CancelRunResponse,
    CreateRunRequest,
    CreateRunResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    GetRunResponse,
    InterruptRunRequest,
    InterruptRunResponse,
    ListSessionsResponse,
    SendMessageRequest,
    SendMessageResponse,
    SessionSkillsResponse,
    SessionSummary,
    SteerRunRequest,
    SteerRunResponse,
    ToolSuggestionsRequest,
    active_run_conflict_detail,
    run_not_found_detail,
    session_not_found_detail,
)
from .session_store import (
    add_run_guidance_message,
    cleanup_finished_runs,
    ensure_session_idle,
    normalize_running_run_state,
    persist_sessions_state,
    release_sync_turn,
    request_run_stop,
    reserve_background_run,
    reserve_sync_turn,
    reset_session_state,
    runs_by_id,
    runs_lock,
    sessions_by_id,
    sessions_lock,
    start_run_session_state,
)


class AgentService:
    """Owns agent operations independent of any transport layer."""

    def __init__(
        self,
        get_ctx: Callable[[], AppContext],
        *,
        emit_progress: Callable[[dict[str, object]], Awaitable[None]] | None = None,
    ) -> None:
        self._get_ctx = get_ctx
        service_utils.set_progress_emitter(emit_progress)

    def set_progress_emitter(
        self,
        emit_progress: Callable[[dict[str, object]], Awaitable[None]] | None,
    ) -> None:
        service_utils.set_progress_emitter(emit_progress)

    def handle_build_completed(self, payload: dict[str, object] | None) -> None:
        service_utils.handle_build_completed(payload)

    def _ctx(self) -> AppContext:
        return self._get_ctx()

    def _ensure_project_scope(
        self,
        session_id: str,
        session: AgentSession,
        project_root: str,
    ) -> None:
        if session.project_root == project_root:
            return

        service_utils.log_agent_event(
            EVENT_SESSION_PROJECT_SWITCHED,
            {
                "session_id": session_id,
                "from_project_root": session.project_root,
                "to_project_root": project_root,
            },
        )
        reset_session_state(session, project_root=project_root)
        persist_sessions_state()

    def _validate_scope(self, project_root: str) -> None:
        try:
            validate_tool_scope(project_root, self._ctx())
        except Exception as exc:
            raise AgentServiceError(400, str(exc)) from exc

    async def create_session(
        self,
        request: CreateSessionRequest,
    ) -> CreateSessionResponse:
        self._validate_scope(request.project_root)

        session_id = uuid.uuid4().hex
        session = AgentSession(session_id=session_id, project_root=request.project_root)
        with sessions_lock:
            sessions_by_id[session_id] = session
        persist_sessions_state()

        service_utils.log_agent_event(
            EVENT_SESSION_CREATED,
            {
                "session_id": session_id,
                "project_root": request.project_root,
            },
        )
        return CreateSessionResponse(
            sessionId=session_id, projectRoot=request.project_root
        )

    async def list_sessions(self, project_root: str) -> ListSessionsResponse:
        self._validate_scope(project_root)
        with sessions_lock:
            sessions = [
                SessionSummary(
                    sessionId=session.session_id,
                    projectRoot=session.project_root,
                    history=list(session.history),
                    recentSelectedTargets=list(session.recent_selected_targets),
                    createdAt=float(session.created_at),
                    updatedAt=float(session.updated_at),
                )
                for session in sessions_by_id.values()
                if session.project_root == project_root
            ]
        sessions.sort(key=lambda session: session.updated_at, reverse=True)
        return ListSessionsResponse(sessions=sessions)

    async def send_message(
        self,
        session_id: str,
        request: SendMessageRequest,
    ) -> SendMessageResponse:
        if not request.message.strip():
            raise AgentServiceError(400, ERROR_MESSAGE_EMPTY)

        cleanup_finished_runs()
        self._validate_scope(request.project_root)

        with sessions_lock:
            session = sessions_by_id.get(session_id)
        if not session:
            raise AgentServiceError(404, session_not_found_detail(session_id))

        reservation_token = reserve_sync_turn(session)
        if reservation_token is None:
            active_run = ensure_session_idle(session)
            conflict_run_id = (
                active_run.run_id if active_run else session.active_run_id or "sync"
            )
            raise AgentServiceError(409, active_run_conflict_detail(conflict_run_id))

        self._ensure_project_scope(session_id, session, request.project_root)
        session.recent_selected_targets = list(request.selected_targets)
        run_id = uuid.uuid4().hex

        service_utils.log_agent_event(
            EVENT_TURN_STARTED,
            {
                "session_id": session_id,
                "run_id": run_id,
                "mode": "sync",
                "project_root": request.project_root,
                "selected_targets": list(request.selected_targets),
                "message": request.message,
            },
        )

        async def emit_progress(payload: dict[str, object]) -> None:
            await service_utils.emit_agent_progress(
                session_id=session_id,
                project_root=request.project_root,
                run_id=run_id,
                payload=payload,
            )

        trace_callback = service_utils.build_run_trace_callback(
            session_id=session_id,
            run_id=run_id,
            project_root=request.project_root,
        )

        try:
            try:
                result = await service_utils.run_turn_with_chain_recovery(
                    session=session,
                    ctx=self._ctx(),
                    project_root=request.project_root,
                    history=list(session.history),
                    user_message=request.message,
                    session_id=session_id,
                    run_id=run_id,
                    selected_targets=request.selected_targets,
                    prior_skill_state=session.skill_state,
                    tool_memory=session.tool_memory,
                    progress_callback=emit_progress,
                    trace_callback=trace_callback,
                )
            except Exception as exc:
                if service_utils.is_chain_integrity_error(str(exc)):
                    service_utils.invalidate_session_response_chain(session)
                    persist_sessions_state()
                await emit_progress({"phase": PHASE_ERROR, "error": str(exc)})
                service_utils.log_agent_event(
                    EVENT_TURN_FAILED,
                    {
                        "session_id": session_id,
                        "run_id": run_id,
                        "mode": "sync",
                        "project_root": request.project_root,
                        "error": str(exc),
                    },
                )
                raise AgentServiceError(500, str(exc)) from exc

            response = service_utils.build_send_message_response(
                session=session,
                user_message=request.message,
                steering_messages=[],
                result=result,
                mode="sync",
                run_id=run_id,
            )
            persist_sessions_state()
            return response
        finally:
            release_sync_turn(session_id, reservation_token)

    async def create_run(
        self,
        session_id: str,
        request: CreateRunRequest,
    ) -> CreateRunResponse:
        if not request.message.strip():
            raise AgentServiceError(400, ERROR_MESSAGE_EMPTY)

        cleanup_finished_runs()
        self._validate_scope(request.project_root)

        with sessions_lock:
            session = sessions_by_id.get(session_id)
        if not session:
            raise AgentServiceError(404, session_not_found_detail(session_id))

        self._ensure_project_scope(session_id, session, request.project_root)

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
            raise AgentServiceError(404, session_not_found_detail(session_id))
        if not reserve_background_run(current, run):
            active_run = ensure_session_idle(current)
            conflict_run_id = (
                active_run.run_id if active_run else current.active_run_id or "sync"
            )
            raise AgentServiceError(409, active_run_conflict_detail(conflict_run_id))

        start_run_session_state(current, run)
        persist_sessions_state()
        service_utils.log_agent_event(
            EVENT_RUN_CREATED,
            {
                "run_id": run_id,
                "session_id": session_id,
                "mode": "background",
                "project_root": request.project_root,
                "selected_targets": list(request.selected_targets),
                "message": request.message,
            },
        )
        run.task = asyncio.create_task(
            service_utils.run_turn_in_background(
                run_id=run_id,
                session_id=session_id,
                ctx=self._ctx(),
            )
        )
        return CreateRunResponse(runId=run_id, status=RUN_STATUS_RUNNING)

    async def get_run(self, session_id: str, run_id: str) -> GetRunResponse:
        cleanup_finished_runs()
        with runs_lock:
            run = runs_by_id.get(run_id)
        if not run or run.session_id != session_id:
            raise AgentServiceError(404, run_not_found_detail(run_id))

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

    async def steer_run(
        self,
        session_id: str,
        run_id: str,
        request: SteerRunRequest,
    ) -> SteerRunResponse:
        message = request.message.strip()
        if not message:
            raise AgentServiceError(400, ERROR_MESSAGE_EMPTY)

        with runs_lock:
            run = runs_by_id.get(run_id)
            if run:
                run = normalize_running_run_state(run)
        if not run or run.session_id != session_id:
            raise AgentServiceError(404, run_not_found_detail(run_id))

        if run.status != RUN_STATUS_RUNNING:
            return SteerRunResponse(runId=run_id, status=run.status, queuedMessages=0)

        with runs_lock:
            current = runs_by_id.get(run_id)
            if current is None:
                raise AgentServiceError(404, run_not_found_detail(run_id))
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
        with sessions_lock:
            current_session = sessions_by_id.get(session_id)
            if current_session is not None:
                add_run_guidance_message(
                    current_session,
                    run_id=run_id,
                    content=message,
                    activity_label=STATUS_TEXT_STEERING,
                    pending_content="Incorporating latest guidance...",
                )

        persist_sessions_state()
        await service_utils.emit_agent_progress(
            session_id=session_id,
            project_root=run_project_root,
            run_id=run_id,
            payload={
                "phase": PHASE_THINKING,
                "status_text": STATUS_TEXT_STEERING,
                "detail_text": DETAIL_TEXT_APPLYING_GUIDANCE,
            },
        )
        service_utils.log_agent_event(
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

    async def cancel_run(self, session_id: str, run_id: str) -> CancelRunResponse:
        with runs_lock:
            run = runs_by_id.get(run_id)
        if not run or run.session_id != session_id:
            raise AgentServiceError(404, run_not_found_detail(run_id))

        if run.status != RUN_STATUS_RUNNING:
            return CancelRunResponse(
                runId=run.run_id, status=run.status, error=run.error
            )

        with runs_lock:
            current = runs_by_id.get(run_id)
            if current:
                current.stop_requested = True
                current.updated_at = time.time()
        with sessions_lock:
            current_session = sessions_by_id.get(session_id)
            if current_session is not None:
                request_run_stop(current_session, run_id)
        persist_sessions_state()

        await service_utils.emit_agent_progress(
            session_id=session_id,
            project_root=run.project_root,
            run_id=run_id,
            payload={
                "phase": PHASE_THINKING,
                "status_text": "Stopping",
                "detail_text": "Finishing the current step before stopping",
            },
        )
        service_utils.log_agent_event(
            EVENT_RUN_STOP_REQUESTED,
            {
                "run_id": run_id,
                "session_id": session_id,
                "project_root": run.project_root,
            },
        )
        return CancelRunResponse(runId=run_id, status=RUN_STATUS_RUNNING, error=None)

    async def interrupt_run(
        self,
        session_id: str,
        run_id: str,
        request: InterruptRunRequest,
    ) -> InterruptRunResponse:
        message = request.message.strip()
        if not message:
            raise AgentServiceError(400, ERROR_MESSAGE_EMPTY)

        with runs_lock:
            run = runs_by_id.get(run_id)
            if run:
                run = normalize_running_run_state(run)
        if not run or run.session_id != session_id:
            raise AgentServiceError(404, run_not_found_detail(run_id))

        if run.status != RUN_STATUS_RUNNING:
            return InterruptRunResponse(
                runId=run_id,
                status=run.status,
                queuedMessages=0,
                queuedMessage=None,
            )

        with runs_lock:
            current = runs_by_id.get(run_id)
            if current is None:
                raise AgentServiceError(404, run_not_found_detail(run_id))
            current = normalize_running_run_state(current)
            if current.status != RUN_STATUS_RUNNING:
                return InterruptRunResponse(
                    runId=run_id,
                    status=current.status,
                    queuedMessages=0,
                    queuedMessage=None,
                )
            current.stop_requested = True
            current.interrupt_messages.append(message)
            current.updated_at = time.time()
            queued_count = len(current.interrupt_messages)
            run_project_root = current.project_root
        with sessions_lock:
            current_session = sessions_by_id.get(session_id)
            if current_session is not None:
                add_run_guidance_message(
                    current_session,
                    run_id=run_id,
                    content=message,
                    activity_label="Interrupting",
                    pending_content="Interrupting after the current step...",
                )

        persist_sessions_state()
        await service_utils.emit_agent_progress(
            session_id=session_id,
            project_root=run_project_root,
            run_id=run_id,
            payload={
                "phase": PHASE_THINKING,
                "status_text": "Interrupting",
                "detail_text": "Will respond after the current step",
            },
        )
        service_utils.log_agent_event(
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
            queuedMessage=message,
        )

    async def get_session_skills(self, session_id: str) -> SessionSkillsResponse:
        with sessions_lock:
            session = sessions_by_id.get(session_id)
        if not session:
            raise AgentServiceError(404, session_not_found_detail(session_id))

        skills_dir = service_utils.orchestrator._config.skills_dir
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
                item
                for item in state.get("selected_skills", [])
                if isinstance(item, dict)
            ],
            reasoning=[
                str(value)
                for value in state.get("reasoning", [])
                if isinstance(value, str)
            ],
            totalChars=int(state.get("total_chars", 0) or 0),
            generatedAt=(
                float(state["generated_at"])
                if isinstance(state.get("generated_at"), (int, float))
                else None
            ),
            loadedSkillsCount=len(selected_skill_ids),
        )

    async def get_tool_directory(
        self,
        session_id: str | None = None,
    ):
        return await tooling.get_tool_directory(session_id)

    async def get_tool_suggestions(self, session_id: str, payload: dict[str, object]):
        request = ToolSuggestionsRequest.model_validate(payload)
        return await tooling.get_tool_suggestions(session_id, request)
