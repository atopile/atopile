"""Pipeline models for the orchestrator framework."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum, auto
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .agents import AgentBackendType


class PipelineStatus(StrEnum):
    """Status of a pipeline."""

    DRAFT = auto()
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()


class TriggerType(StrEnum):
    """Type of pipeline trigger."""

    MANUAL = auto()
    TIMER = auto()
    WEBHOOK = auto()


# Node data types


class AgentNodeData(BaseModel):
    """Data for an agent node."""

    name: str
    backend: AgentBackendType = AgentBackendType.CLAUDE_CODE
    prompt: str = ""
    system_prompt: str | None = None
    planning_file: str | None = None
    max_turns: int | None = None
    max_budget_usd: float | None = None
    working_directory: str | None = None
    environment: dict[str, str] | None = None


class TriggerNodeData(BaseModel):
    """Data for a trigger node."""

    trigger_type: TriggerType = TriggerType.MANUAL
    interval_seconds: int | None = None
    cron_expression: str | None = None


class WaitNodeData(BaseModel):
    """Data for a wait node."""

    duration_seconds: int = 60  # How long to wait


class ConditionNodeData(BaseModel):
    """Data for a condition node.

    Evaluates conditions and routes to left (true) or right (false) output.
    All conditions are optional - if none specified, always evaluates to true.
    If multiple conditions specified, ALL must be true (AND logic).
    """

    # Count condition: true if current count < limit
    count_limit: int | None = None

    # Time condition: true if time since session start < limit
    time_limit_seconds: int | None = None


class PipelineNodePosition(BaseModel):
    """Position of a node in the editor."""

    x: float
    y: float


class PipelineNode(BaseModel):
    """A node in the pipeline."""

    id: str
    type: Literal["agent", "trigger", "condition", "wait"]
    position: PipelineNodePosition
    data: AgentNodeData | TriggerNodeData | ConditionNodeData | WaitNodeData

    @model_validator(mode="before")
    @classmethod
    def validate_data_type(cls, values):
        """Ensure data is parsed with the correct type based on node type."""
        if isinstance(values, dict):
            node_type = values.get("type")
            data = values.get("data")

            if isinstance(data, dict):
                # Parse data with the correct model based on type
                if node_type == "agent":
                    values["data"] = AgentNodeData.model_validate(data)
                elif node_type == "trigger":
                    values["data"] = TriggerNodeData.model_validate(data)
                elif node_type == "condition":
                    values["data"] = ConditionNodeData.model_validate(data)
                elif node_type == "wait":
                    values["data"] = WaitNodeData.model_validate(data)

        return values


class PipelineEdge(BaseModel):
    """An edge connecting nodes in the pipeline."""

    id: str
    source: str
    target: str
    source_handle: str | None = None
    label: str | None = None


class PipelineConfig(BaseModel):
    """Configuration for pipeline execution."""

    parallel_execution: bool = False
    stop_on_failure: bool = True
    notification_webhook: str | None = None


class PipelineState(BaseModel):
    """Full state of a pipeline."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str | None = None
    nodes: list[PipelineNode] = Field(default_factory=list)
    edges: list[PipelineEdge] = Field(default_factory=list)
    config: PipelineConfig = Field(default_factory=PipelineConfig)
    status: PipelineStatus = PipelineStatus.DRAFT
    current_node_id: str | None = None
    execution_history: list[str] = Field(default_factory=list)  # List of agent IDs
    node_agent_map: dict[str, str] = Field(default_factory=dict)  # node_id -> agent_id
    node_status: dict[str, str] = Field(default_factory=dict)  # node_id -> status
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()

    def is_running(self) -> bool:
        """Check if the pipeline is currently running."""
        return self.status in (PipelineStatus.RUNNING, PipelineStatus.PAUSED)

    def is_finished(self) -> bool:
        """Check if the pipeline has finished execution."""
        return self.status in (PipelineStatus.COMPLETED, PipelineStatus.FAILED)


# API Request/Response Models


class CreatePipelineRequest(BaseModel):
    """Request to create a new pipeline."""

    name: str
    description: str | None = None
    nodes: list[PipelineNode] = Field(default_factory=list)
    edges: list[PipelineEdge] = Field(default_factory=list)
    config: PipelineConfig = Field(default_factory=PipelineConfig)


class UpdatePipelineRequest(BaseModel):
    """Request to update a pipeline."""

    name: str | None = None
    description: str | None = None
    nodes: list[PipelineNode] | None = None
    edges: list[PipelineEdge] | None = None
    config: PipelineConfig | None = None


class PipelineListResponse(BaseModel):
    """Response containing list of pipelines."""

    pipelines: list[PipelineState]
    total: int


class PipelineStateResponse(BaseModel):
    """Response containing pipeline state."""

    pipeline: PipelineState


class PipelineActionResponse(BaseModel):
    """Response for pipeline actions (run, pause, stop)."""

    status: str
    message: str
    pipeline_id: str


class PipelineSessionStatus(StrEnum):
    """Status of a pipeline session/execution."""

    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    STOPPED = auto()


class PipelineSession(BaseModel):
    """Represents a single execution/run of a pipeline.

    Each time a pipeline is triggered, a new session is created.
    This allows tracking multiple concurrent or historical executions.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_id: str
    status: PipelineSessionStatus = PipelineSessionStatus.RUNNING
    node_agent_map: dict[str, str] = Field(default_factory=dict)  # node_id -> agent_id
    node_status: dict[str, str] = Field(default_factory=dict)  # node_id -> status
    wait_until: dict[str, datetime] = Field(default_factory=dict)  # wait_node_id -> resume datetime
    condition_counts: dict[str, int] = Field(default_factory=dict)  # condition_node_id -> evaluation count
    execution_order: list[str] = Field(default_factory=list)  # Order nodes were executed
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = None
    error_message: str | None = None

    def is_running(self) -> bool:
        """Check if session is still running."""
        return self.status == PipelineSessionStatus.RUNNING

    def is_finished(self) -> bool:
        """Check if session has finished."""
        return self.status in (
            PipelineSessionStatus.COMPLETED,
            PipelineSessionStatus.FAILED,
            PipelineSessionStatus.STOPPED,
        )


class PipelineSessionResponse(BaseModel):
    """Response containing a single pipeline session."""

    session: PipelineSession


class PipelineSessionListResponse(BaseModel):
    """Response containing list of pipeline sessions."""

    sessions: list[PipelineSession]
    total: int
