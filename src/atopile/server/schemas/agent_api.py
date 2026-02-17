"""Pydantic API schemas for agent HTTP and event payloads."""

from __future__ import annotations

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
    usage: AgentProgressUsage | None = None
