"""Session models for the orchestrator framework."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum, auto
from typing import Any

from pydantic import BaseModel, Field

from .agents import AgentBackendType


class SessionStatus(StrEnum):
    """Status of a session."""

    ACTIVE = auto()
    PAUSED = auto()
    COMPLETED = auto()
    ABANDONED = auto()


class SessionMetadata(BaseModel):
    """Metadata about a session."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    backend: AgentBackendType
    backend_session_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    working_directory: str | None = None
    initial_prompt: str | None = None
    total_turns: int = 0
    total_cost_usd: float = 0.0
    tags: list[str] = Field(default_factory=list)
    custom_data: dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    """Full state of a session, including history."""

    metadata: SessionMetadata
    status: SessionStatus = SessionStatus.ACTIVE
    agent_runs: list[str] = Field(default_factory=list)  # List of agent IDs
    last_agent_id: str | None = None

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.metadata.updated_at = datetime.now()


# API Request/Response Models


class SessionListResponse(BaseModel):
    """Response containing list of sessions."""

    sessions: list[SessionMetadata]
    total: int


class SessionStateResponse(BaseModel):
    """Response containing session state."""

    session: SessionState


class ResumeSessionRequest(BaseModel):
    """Request to resume a session."""

    prompt: str
    max_turns: int | None = None
    timeout_seconds: int | None = None


class ResumeSessionResponse(BaseModel):
    """Response after resuming a session."""

    agent_id: str
    session_id: str
    message: str = "Session resumed successfully"
