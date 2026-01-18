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


class LoopNodeData(BaseModel):
    """Data for a loop node."""

    duration_seconds: int = 3600
    restart_on_complete: bool = True
    restart_on_fail: bool = False
    max_iterations: int | None = None


class ConditionNodeData(BaseModel):
    """Data for a condition node."""

    expression: str = ""


class PipelineNodePosition(BaseModel):
    """Position of a node in the editor."""

    x: float
    y: float


class PipelineNode(BaseModel):
    """A node in the pipeline."""

    id: str
    type: Literal["agent", "trigger", "condition", "loop"]
    position: PipelineNodePosition
    data: AgentNodeData | TriggerNodeData | LoopNodeData | ConditionNodeData

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
                elif node_type == "loop":
                    values["data"] = LoopNodeData.model_validate(data)
                elif node_type == "condition":
                    values["data"] = ConditionNodeData.model_validate(data)

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
