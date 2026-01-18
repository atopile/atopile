"""Event and output models for the orchestrator framework."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum, auto
from typing import Any

from pydantic import BaseModel, Field


class OutputType(StrEnum):
    """Type of output chunk from an agent."""

    # Structured message types (from claude-code --output-format stream-json)
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    RESULT = "result"

    # Streaming types (partial messages)
    TEXT_DELTA = "text_delta"  # Streaming text chunk
    STREAM_START = "stream_start"  # Message stream started
    STREAM_STOP = "stream_stop"  # Message stream ended

    # Meta types
    ERROR = "error"
    STATUS = "status"
    RAW = "raw"
    INIT = "init"


class OutputChunk(BaseModel):
    """A chunk of output from an agent."""

    type: OutputType
    timestamp: datetime = Field(default_factory=datetime.now)
    content: str | None = None
    data: dict[str, Any] | None = None
    raw_line: str | None = None

    # For tool_use chunks
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None

    # For tool_result chunks
    tool_result: Any | None = None
    is_error: bool = False

    # Sequence number for ordering
    sequence: int = 0


class StreamEventType(StrEnum):
    """Type of WebSocket stream event."""

    # Connection events
    CONNECTED = auto()
    DISCONNECTED = auto()

    # Agent lifecycle events
    AGENT_STARTED = auto()
    AGENT_OUTPUT = auto()
    AGENT_COMPLETED = auto()
    AGENT_FAILED = auto()
    AGENT_TERMINATED = auto()

    # Error events
    ERROR = auto()

    # Heartbeat
    PING = auto()
    PONG = auto()


class StreamEvent(BaseModel):
    """Event sent over WebSocket connection."""

    type: StreamEventType
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    data: dict[str, Any] | None = None
    chunk: OutputChunk | None = None
    message: str | None = None


class ClaudeCodeMessage(BaseModel):
    """Parsed message from claude-code stream-json output.

    Claude code outputs JSON lines with varying structure.
    Common fields:
    - type: message type (system, assistant, user, tool_use, tool_result, result)
    - content: list of content blocks or string
    - session_id: present in init/system messages
    """

    type: str
    content: list[dict[str, Any]] | str | None = None
    session_id: str | None = None
    role: str | None = None
    model: str | None = None
    stop_reason: str | None = None
    usage: dict[str, Any] | None = None

    # Tool-related fields
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_result: Any | None = None
    is_error: bool | None = None

    # Result fields
    result: str | None = None
    cost_usd: float | None = None
    total_cost_usd: float | None = None
    duration_ms: int | None = None
    duration_api_ms: int | None = None
    num_turns: int | None = None

    # Raw data for extension
    raw: dict[str, Any] | None = None

    @classmethod
    def from_json_line(cls, line: str) -> ClaudeCodeMessage | None:
        """Parse a JSON line from claude-code output."""
        import json

        line = line.strip()
        if not line:
            return None

        try:
            data = json.loads(line)
            if not isinstance(data, dict):
                return None

            msg = cls(
                type=data.get("type", "unknown"),
                content=data.get("content"),
                session_id=data.get("session_id"),
                role=data.get("role"),
                model=data.get("model"),
                stop_reason=data.get("stop_reason"),
                usage=data.get("usage"),
                tool_name=data.get("tool_name"),
                tool_input=data.get("tool_input"),
                tool_result=data.get("tool_result"),
                is_error=data.get("is_error"),
                result=data.get("result"),
                cost_usd=data.get("cost_usd"),
                total_cost_usd=data.get("total_cost_usd"),
                duration_ms=data.get("duration_ms"),
                duration_api_ms=data.get("duration_api_ms"),
                num_turns=data.get("num_turns"),
                raw=data,
            )
            return msg
        except json.JSONDecodeError:
            return None

    def to_output_chunk(self, sequence: int = 0) -> OutputChunk | None:
        """Convert to an OutputChunk.

        Returns None for events that should be skipped (e.g., internal stream events).
        """
        output_type = OutputType.RAW
        content_str = None
        tool_name = self.tool_name
        tool_input = self.tool_input
        tool_result = self.tool_result
        is_error = self.is_error or False

        if self.type == "system":
            output_type = OutputType.SYSTEM
        elif self.type == "assistant":
            # Check if this is a tool_use message (content contains tool_use blocks)
            message = self.raw.get("message", {}) if self.raw else {}
            message_content = message.get("content", [])
            if isinstance(message_content, list):
                # Check for tool_use blocks
                for block in message_content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        output_type = OutputType.TOOL_USE
                        tool_name = block.get("name")
                        tool_input = block.get("input")
                        content_str = tool_name
                        break
                else:
                    # No tool_use, extract text content
                    output_type = OutputType.ASSISTANT
                    text_parts = []
                    for block in message_content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    if text_parts:
                        content_str = "".join(text_parts)
            else:
                output_type = OutputType.ASSISTANT
        elif self.type == "user":
            # Check if this is a tool_result message
            message = self.raw.get("message", {}) if self.raw else {}
            message_content = message.get("content", [])
            if isinstance(message_content, list):
                for block in message_content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        output_type = OutputType.TOOL_RESULT
                        tool_result = block.get("content", "")
                        is_error = block.get("is_error", False)
                        break
                else:
                    output_type = OutputType.USER
            else:
                output_type = OutputType.USER
        elif self.type == "tool_use":
            output_type = OutputType.TOOL_USE
        elif self.type == "tool_result":
            output_type = OutputType.TOOL_RESULT
        elif self.type == "result":
            output_type = OutputType.RESULT
        elif self.type == "init":
            output_type = OutputType.INIT
        elif self.type == "stream_event":
            # Handle streaming events from --include-partial-messages
            event = self.raw.get("event", {}) if self.raw else {}
            event_type = event.get("type", "")

            if event_type == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    output_type = OutputType.TEXT_DELTA
                    content_str = delta.get("text", "")
                else:
                    return None  # Skip non-text deltas
            elif event_type == "message_start":
                output_type = OutputType.STREAM_START
            elif event_type == "message_stop":
                output_type = OutputType.STREAM_STOP
            else:
                return None  # Skip other stream events (content_block_start, etc.)

        # Extract content string for non-stream types if not already set
        if content_str is None:
            if isinstance(self.content, str):
                content_str = self.content
            elif isinstance(self.content, list):
                # Join text content blocks
                text_parts = []
                for block in self.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                if text_parts:
                    content_str = "".join(text_parts)

        return OutputChunk(
            type=output_type,
            content=content_str,
            data=self.raw,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_result=tool_result,
            is_error=is_error,
            sequence=sequence,
        )
