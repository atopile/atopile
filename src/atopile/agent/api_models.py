"""Shared agent API/runtime models for the rewrite-native agent service."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base API model with alias population enabled."""

    model_config = ConfigDict(populate_by_name=True)


class ToolTraceResponse(BaseModel):
    name: str
    args: dict[str, Any]
    ok: bool
    result: dict[str, Any]


class ToolDirectoryItem(ApiModel):
    name: str
    category: str
    purpose: str
    tooltip: str
    inputs: list[str]
    typical_output: str = Field(alias="typicalOutput")
    keywords: list[str]


class ToolSuggestion(ApiModel):
    name: str
    category: str
    score: float
    reason: str
    tooltip: str
    prefilled_args: dict[str, Any] = Field(alias="prefilledArgs")
    prefilled_prompt: str | None = Field(alias="prefilledPrompt")
    kind: Literal["tool", "composite"]


class ToolMemoryEntry(ApiModel):
    tool_name: str = Field(alias="toolName")
    summary: str
    ok: bool
    updated_at: float = Field(alias="updatedAt")
    age_seconds: float = Field(alias="ageSeconds")
    stale: bool
    stale_hint: str | None = Field(alias="staleHint")
    context_id: str | None = Field(alias="contextId")


class CreateSessionRequest(ApiModel):
    project_root: str = Field(alias="projectRoot")


class CreateSessionResponse(ApiModel):
    session_id: str = Field(alias="sessionId")
    project_root: str = Field(alias="projectRoot")


class SessionHistoryMessage(ApiModel):
    role: str
    content: str


class SessionSummary(ApiModel):
    session_id: str = Field(alias="sessionId")
    project_root: str = Field(alias="projectRoot")
    history: list[SessionHistoryMessage] = Field(default_factory=list)
    recent_selected_targets: list[str] = Field(
        default_factory=list, alias="recentSelectedTargets"
    )
    created_at: float = Field(alias="createdAt")
    updated_at: float = Field(alias="updatedAt")


class ListSessionsResponse(ApiModel):
    sessions: list[SessionSummary] = Field(default_factory=list)


class SendMessageRequest(ApiModel):
    message: str
    project_root: str = Field(alias="projectRoot")
    selected_targets: list[str] = Field(default_factory=list, alias="selectedTargets")


class SendMessageResponse(ApiModel):
    session_id: str = Field(alias="sessionId")
    assistant_message: str = Field(alias="assistantMessage")
    model: str
    tool_traces: list[ToolTraceResponse] = Field(alias="toolTraces")
    tool_suggestions: list[ToolSuggestion] = Field(alias="toolSuggestions")
    tool_memory: list[ToolMemoryEntry] = Field(alias="toolMemory")


class ToolDirectoryResponse(ApiModel):
    tools: list[ToolDirectoryItem]
    categories: list[str]
    suggestions: list[ToolSuggestion]
    tool_memory: list[ToolMemoryEntry] = Field(alias="toolMemory")


class ToolSuggestionsRequest(ApiModel):
    message: str = ""
    project_root: str | None = Field(default=None, alias="projectRoot")
    selected_targets: list[str] = Field(default_factory=list, alias="selectedTargets")


class ToolSuggestionsResponse(ApiModel):
    suggestions: list[ToolSuggestion]
    tool_memory: list[ToolMemoryEntry] = Field(alias="toolMemory")


class SessionSkillsResponse(ApiModel):
    session_id: str = Field(alias="sessionId")
    project_root: str = Field(alias="projectRoot")
    skills_dir: str = Field(alias="skillsDir")
    selected_skill_ids: list[str] = Field(
        default_factory=list, alias="selectedSkillIds"
    )
    selected_skills: list[dict[str, Any]] = Field(
        default_factory=list, alias="selectedSkills"
    )
    reasoning: list[str] = Field(default_factory=list)
    total_chars: int = Field(default=0, alias="totalChars")
    generated_at: float | None = Field(default=None, alias="generatedAt")
    loaded_skills_count: int = Field(default=0, alias="loadedSkillsCount")


class CreateRunRequest(ApiModel):
    message: str
    project_root: str = Field(alias="projectRoot")
    selected_targets: list[str] = Field(default_factory=list, alias="selectedTargets")


class CreateRunResponse(ApiModel):
    run_id: str = Field(alias="runId")
    status: str


class GetRunResponse(ApiModel):
    run_id: str = Field(alias="runId")
    status: str
    response: SendMessageResponse | None = None
    error: str | None = None


class CancelRunResponse(ApiModel):
    run_id: str = Field(alias="runId")
    status: str
    error: str | None = None


class SteerRunRequest(ApiModel):
    message: str


class SteerRunResponse(ApiModel):
    run_id: str = Field(alias="runId")
    status: str
    queued_messages: int = Field(alias="queuedMessages")


class AgentProgressUsage(ApiModel):
    input_tokens: int | None = Field(default=None, alias="inputTokens")
    output_tokens: int | None = Field(default=None, alias="outputTokens")
    total_tokens: int | None = Field(default=None, alias="totalTokens")
    reasoning_tokens: int | None = Field(default=None, alias="reasoningTokens")
    cached_input_tokens: int | None = Field(default=None, alias="cachedInputTokens")


class AgentProgressEventPayload(ApiModel):
    session_id: str | None = Field(default=None, alias="sessionId")
    project_root: str | None = Field(default=None, alias="projectRoot")
    run_id: str | None = Field(default=None, alias="runId")
    phase: str | None = None
    call_id: str | None = Field(default=None, alias="callId")
    name: str | None = None
    args: dict[str, Any] | None = None
    trace: ToolTraceResponse | None = None
    status_text: str | None = Field(default=None, alias="statusText")
    detail_text: str | None = Field(default=None, alias="detailText")
    loop: int | None = None
    tool_index: int | None = Field(default=None, alias="toolIndex")
    tool_count: int | None = Field(default=None, alias="toolCount")
    input_tokens: int | None = Field(default=None, alias="inputTokens")
    output_tokens: int | None = Field(default=None, alias="outputTokens")
    total_tokens: int | None = Field(default=None, alias="totalTokens")
    reasoning_tokens: int | None = Field(default=None, alias="reasoningTokens")
    cached_input_tokens: int | None = Field(default=None, alias="cachedInputTokens")
    usage: AgentProgressUsage | None = None
    response: SendMessageResponse | None = None
    error: str | None = None


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
EVENT_RUN_STOP_REQUESTED = "run_stop_requested"
EVENT_RUN_STEER_QUEUED = "run_steer_queued"
EVENT_RUN_STEER_CONSUMED = "run_steer_consumed"
EVENT_RUN_INTERRUPT_QUEUED = "run_interrupt_queued"
EVENT_RUN_INTERRUPT_CONSUMED = "run_interrupt_consumed"

USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"


class AgentSession(BaseModel):
    """In-memory state for a single agent chat session."""

    session_id: str
    project_root: str
    history: list[dict[str, str]] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_memory: dict[str, dict[str, Any]] = Field(default_factory=dict)
    recent_selected_targets: list[str] = Field(default_factory=list)
    active_run_id: str | None = None
    activity_label: str = "Ready"
    error: str | None = None
    run_started_at: float | None = None
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
    consumed_steer_messages: list[str] = Field(default_factory=list)
    interrupt_messages: list[str] = Field(default_factory=list)
    consumed_interrupt_messages: list[str] = Field(default_factory=list)
    stop_requested: bool = False


class InterruptRunRequest(ApiModel):
    message: str


class InterruptRunResponse(ApiModel):
    run_id: str = Field(alias="runId")
    status: str
    queued_messages: int = Field(alias="queuedMessages")
    queued_message: str | None = Field(default=None, alias="queuedMessage")


class AgentServiceError(Exception):
    """Typed service error that can be mapped onto RPC action results."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def session_not_found_detail(session_id: str) -> str:
    return f"Session not found: {session_id}"


def run_not_found_detail(run_id: str) -> str:
    return f"Run not found: {run_id}"


def active_run_conflict_detail(run_id: str) -> str:
    return f"Another agent run is already active for this session (run_id={run_id})."
