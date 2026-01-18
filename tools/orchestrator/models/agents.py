"""Agent-related models for the orchestrator framework."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum, auto
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(StrEnum):
    """Status of an agent."""

    PENDING = auto()
    STARTING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    TERMINATED = auto()


class AgentBackendType(StrEnum):
    """Supported agent backend types."""

    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    CURSOR = "cursor"


class AgentCapabilities(BaseModel):
    """Capabilities of an agent backend."""

    streaming: bool = True
    resume: bool = False
    session_persistence: bool = False
    input_during_run: bool = False
    tools: bool = False
    budget_control: bool = False
    max_turns: bool = False
    allowed_tools: bool = False


class AgentConfig(BaseModel):
    """Configuration for spawning an agent."""

    backend: AgentBackendType = AgentBackendType.CLAUDE_CODE
    prompt: str
    working_directory: str | None = None
    session_id: str | None = None
    resume_session: bool = False
    max_turns: int | None = None
    max_budget_usd: float | None = None
    allowed_tools: list[str] | None = None
    disallowed_tools: list[str] | None = None
    system_prompt: str | None = None
    model: str | None = None
    timeout_seconds: int | None = None
    environment: dict[str, str] | None = None
    extra_args: list[str] | None = None


class AgentState(BaseModel):
    """Runtime state of an agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str | None = None  # Human-readable name (e.g., "my-pipeline.worker-a")
    config: AgentConfig
    status: AgentStatus = AgentStatus.PENDING
    pid: int | None = None
    exit_code: int | None = None
    error_message: str | None = None
    session_id: str | None = None
    pipeline_id: str | None = None  # ID of the pipeline this agent belongs to
    node_id: str | None = None  # ID of the pipeline node this agent was spawned from
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    output_chunks: int = 0
    last_activity_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_running(self) -> bool:
        """Check if the agent is currently running."""
        return self.status in (
            AgentStatus.PENDING, AgentStatus.STARTING, AgentStatus.RUNNING
        )

    def is_finished(self) -> bool:
        """Check if the agent has finished (successfully or not)."""
        return self.status in (
            AgentStatus.COMPLETED,
            AgentStatus.FAILED,
            AgentStatus.TERMINATED,
        )

    def duration_seconds(self) -> float | None:
        """Calculate the duration of the agent run in seconds."""
        if self.started_at is None:
            return None
        end = self.finished_at or datetime.now()
        return (end - self.started_at).total_seconds()


# API Request/Response Models


class SpawnAgentRequest(BaseModel):
    """Request to spawn a new agent."""

    config: AgentConfig
    name: str | None = None  # Optional human-readable name


class UpdateAgentRequest(BaseModel):
    """Request to update an agent's metadata."""

    name: str | None = None


class SpawnAgentResponse(BaseModel):
    """Response after spawning an agent."""

    agent_id: str
    status: AgentStatus
    message: str = "Agent spawned successfully"


class AgentStateResponse(BaseModel):
    """Response containing agent state."""

    agent: AgentState


class AgentListResponse(BaseModel):
    """Response containing list of agents."""

    agents: list[AgentState]
    total: int


class TerminateAgentRequest(BaseModel):
    """Request to terminate an agent."""

    force: bool = False
    timeout_seconds: float = 5.0


class TerminateAgentResponse(BaseModel):
    """Response after terminating an agent."""

    agent_id: str
    success: bool
    message: str


class SendInputRequest(BaseModel):
    """Request to send input to an agent."""

    input: str
    newline: bool = True


class SendInputResponse(BaseModel):
    """Response after sending input."""

    success: bool
    message: str


class ResumeAgentRequest(BaseModel):
    """Request to resume a completed agent with a new prompt."""

    prompt: str
    max_turns: int | None = None
    max_budget_usd: float | None = None


class AgentOutputResponse(BaseModel):
    """Response containing buffered agent output."""

    agent_id: str
    chunks: list[Any]  # List of OutputChunk
    total_chunks: int
