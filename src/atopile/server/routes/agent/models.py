"""Runtime models/constants for agent routes plus schema re-exports."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from atopile.server.schemas import agent_api as _agent_api

ApiModel = _agent_api.ApiModel
CreateSessionRequest = _agent_api.CreateSessionRequest
CreateSessionResponse = _agent_api.CreateSessionResponse
SendMessageRequest = _agent_api.SendMessageRequest
ToolTraceResponse = _agent_api.ToolTraceResponse
SendMessageResponse = _agent_api.SendMessageResponse
ToolDirectoryResponse = _agent_api.ToolDirectoryResponse
ToolSuggestionsRequest = _agent_api.ToolSuggestionsRequest
ToolSuggestionsResponse = _agent_api.ToolSuggestionsResponse
SessionSkillsResponse = _agent_api.SessionSkillsResponse
CreateRunRequest = _agent_api.CreateRunRequest
CreateRunResponse = _agent_api.CreateRunResponse
GetRunResponse = _agent_api.GetRunResponse
CancelRunResponse = _agent_api.CancelRunResponse
SteerRunRequest = _agent_api.SteerRunRequest
SteerRunResponse = _agent_api.SteerRunResponse

DEFAULT_AGENT_ID = "manager"
WORKER_AGENT_ID = "worker"
OTHER_CATEGORY = "other"

RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_CANCELLED = "cancelled"

TURN_MODE_SYNC = "sync"
TURN_MODE_BACKGROUND = "background"

PHASE_ERROR = "error"
PHASE_THINKING = "thinking"
PHASE_STOPPED = "stopped"

STATUS_TEXT_STEERING = "Steering"
DETAIL_TEXT_APPLYING_GUIDANCE = "Applying latest user guidance"
REASON_CANCELLED_BY_USER = "cancelled_by_user"

ERROR_MESSAGE_EMPTY = "message must not be empty"
ERROR_CANCELLED = "Cancelled"
ERROR_CANCELLED_BY_USER = "Cancelled by user"
ERROR_RUN_TASK_ENDED = "Run task ended unexpectedly"
ERROR_SESSION_EXPIRED = "Session expired before run completion"

DETAIL_PROJECT_ROOT_MISMATCH = "projectRoot must match the active session project"

EVENT_AGENT_PROGRESS = "agent_progress"
EVENT_AGENT_MESSAGE = "agent_message"
EVENT_SESSION_CREATED = "session_created"
EVENT_SESSION_PROJECT_SWITCHED = "session_project_switched"
EVENT_TURN_STARTED = "turn_started"
EVENT_TURN_COMPLETED = "turn_completed"
EVENT_TURN_FAILED = "turn_failed"
EVENT_RUN_CREATED = "run_created"
EVENT_RUN_PROGRESS = "run_progress"
EVENT_RUN_COMPLETED = "run_completed"
EVENT_RUN_FAILED = "run_failed"
EVENT_RUN_CANCELLED = "run_cancelled"
EVENT_RUN_STEER_QUEUED = "run_steer_queued"
EVENT_RUN_STEER_CONSUMED = "run_steer_consumed"

USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"


class AgentSession(BaseModel):
    """In-memory state for a single agent chat session."""

    session_id: str
    project_root: str
    history: list[dict[str, str]] = Field(default_factory=list)
    tool_memory: dict[str, dict[str, Any]] = Field(default_factory=dict)
    recent_selected_targets: list[str] = Field(default_factory=list)
    active_run_id: str | None = None
    last_response_id: str | None = None
    conversation_id: str | None = None
    skill_state: dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class AgentRun(BaseModel):
    """In-memory state for a background run."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: str
    session_id: str
    message: str
    project_root: str
    selected_targets: list[str] = Field(default_factory=list)
    status: str = RUN_STATUS_RUNNING
    response_payload: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    task: asyncio.Task[Any] | None = Field(default=None, repr=False)
    steer_messages: list[str] = Field(default_factory=list)
    message_log: list[dict[str, Any]] = Field(default_factory=list)
    inbox_cursor: dict[str, int] = Field(
        default_factory=lambda: {DEFAULT_AGENT_ID: 0, WORKER_AGENT_ID: 0}
    )
    pending_acks: set[str] = Field(default_factory=set)
    intent_snapshot: dict[str, Any] = Field(default_factory=dict)


class AgentPeerMessageResponse(ApiModel):
    message_id: str = Field(alias="messageId")
    thread_id: str = Field(alias="threadId")
    from_agent: str = Field(alias="fromAgent")
    to_agent: str = Field(alias="toAgent")
    kind: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    visibility: str
    priority: str
    requires_ack: bool = Field(alias="requiresAck")
    correlation_id: str | None = Field(default=None, alias="correlationId")
    parent_id: str | None = Field(default=None, alias="parentId")
    created_at: float = Field(alias="createdAt")


class GetRunMessagesResponse(ApiModel):
    run_id: str = Field(alias="runId")
    session_id: str = Field(alias="sessionId")
    count: int
    pending_acks: int = Field(alias="pendingAcks")
    messages: list[AgentPeerMessageResponse] = Field(default_factory=list)


def session_not_found_detail(session_id: str) -> str:
    return f"Session not found: {session_id}"


def run_not_found_detail(run_id: str) -> str:
    return f"Run not found: {run_id}"


def active_run_conflict_detail(run_id: str) -> str:
    return f"Another agent run is already active for this session (run_id={run_id})."
