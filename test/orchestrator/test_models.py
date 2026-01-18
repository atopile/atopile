"""Tests for orchestrator models."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from tools.orchestrator.models import (
    AgentBackendType,
    AgentCapabilities,
    AgentConfig,
    AgentState,
    AgentStatus,
    ClaudeCodeMessage,
    OutputChunk,
    OutputType,
    SessionMetadata,
    SessionState,
    SessionStatus,
    SpawnAgentRequest,
    StreamEvent,
    StreamEventType,
)


class TestAgentModels:
    """Tests for agent-related models."""

    def test_agent_status_values(self):
        """Test AgentStatus enum values."""
        assert AgentStatus.PENDING.value == "pending"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.FAILED.value == "failed"
        assert AgentStatus.TERMINATED.value == "terminated"

    def test_agent_backend_type_values(self):
        """Test AgentBackendType enum values."""
        assert AgentBackendType.CLAUDE_CODE.value == "claude-code"
        assert AgentBackendType.CODEX.value == "codex"
        assert AgentBackendType.CURSOR.value == "cursor"

    def test_agent_config_defaults(self):
        """Test AgentConfig default values."""
        config = AgentConfig(prompt="test prompt")
        assert config.backend == AgentBackendType.CLAUDE_CODE
        assert config.prompt == "test prompt"
        assert config.working_directory is None
        assert config.max_turns is None

    def test_agent_config_full(self):
        """Test AgentConfig with all fields."""
        config = AgentConfig(
            backend=AgentBackendType.CLAUDE_CODE,
            prompt="test prompt",
            working_directory="/tmp",
            session_id="session-123",
            resume_session=True,
            max_turns=10,
            max_budget_usd=1.5,
            allowed_tools=["Read", "Write"],
            disallowed_tools=["Bash"],
            system_prompt="Be helpful",
            model="sonnet",
        )
        assert config.backend == AgentBackendType.CLAUDE_CODE
        assert config.max_turns == 10
        assert config.allowed_tools == ["Read", "Write"]

    def test_agent_state_id_generated(self):
        """Test that AgentState generates an ID."""
        config = AgentConfig(prompt="test")
        state = AgentState(config=config)
        assert state.id is not None
        assert len(state.id) == 36  # UUID format

    def test_agent_state_is_running(self):
        """Test AgentState.is_running()."""
        config = AgentConfig(prompt="test")

        pending = AgentState(config=config, status=AgentStatus.PENDING)
        assert pending.is_running() is True

        running = AgentState(config=config, status=AgentStatus.RUNNING)
        assert running.is_running() is True

        completed = AgentState(config=config, status=AgentStatus.COMPLETED)
        assert completed.is_running() is False

        failed = AgentState(config=config, status=AgentStatus.FAILED)
        assert failed.is_running() is False

    def test_agent_state_is_finished(self):
        """Test AgentState.is_finished()."""
        config = AgentConfig(prompt="test")

        pending = AgentState(config=config, status=AgentStatus.PENDING)
        assert pending.is_finished() is False

        completed = AgentState(config=config, status=AgentStatus.COMPLETED)
        assert completed.is_finished() is True

        failed = AgentState(config=config, status=AgentStatus.FAILED)
        assert failed.is_finished() is True

        terminated = AgentState(config=config, status=AgentStatus.TERMINATED)
        assert terminated.is_finished() is True

    def test_agent_state_duration(self):
        """Test AgentState.duration_seconds()."""
        config = AgentConfig(prompt="test")
        state = AgentState(config=config)

        # No start time
        assert state.duration_seconds() is None

        # With start time
        state.started_at = datetime.now()
        duration = state.duration_seconds()
        assert duration is not None
        assert duration >= 0

    def test_agent_capabilities(self):
        """Test AgentCapabilities model."""
        caps = AgentCapabilities()
        assert caps.streaming is True
        assert caps.resume is False

        caps = AgentCapabilities(resume=True, tools=True)
        assert caps.resume is True
        assert caps.tools is True

    def test_spawn_agent_request(self):
        """Test SpawnAgentRequest model."""
        config = AgentConfig(prompt="test")
        request = SpawnAgentRequest(config=config)
        assert request.config.prompt == "test"


class TestEventModels:
    """Tests for event-related models."""

    def test_output_type_values(self):
        """Test OutputType enum values."""
        assert OutputType.SYSTEM.value == "system"
        assert OutputType.ASSISTANT.value == "assistant"
        assert OutputType.TOOL_USE.value == "tool_use"
        assert OutputType.ERROR.value == "error"
        assert OutputType.RAW.value == "raw"

    def test_output_chunk_defaults(self):
        """Test OutputChunk default values."""
        chunk = OutputChunk(type=OutputType.RAW)
        assert chunk.timestamp is not None
        assert chunk.content is None
        assert chunk.sequence == 0

    def test_output_chunk_full(self):
        """Test OutputChunk with all fields."""
        chunk = OutputChunk(
            type=OutputType.TOOL_USE,
            content="Using tool",
            tool_name="Read",
            tool_input={"path": "/tmp/file.txt"},
            sequence=42,
        )
        assert chunk.type == OutputType.TOOL_USE
        assert chunk.tool_name == "Read"
        assert chunk.sequence == 42

    def test_stream_event_type_values(self):
        """Test StreamEventType enum values."""
        assert StreamEventType.CONNECTED.value == "connected"
        assert StreamEventType.AGENT_STARTED.value == "agent_started"
        assert StreamEventType.AGENT_OUTPUT.value == "agent_output"

    def test_stream_event(self):
        """Test StreamEvent model."""
        chunk = OutputChunk(type=OutputType.ASSISTANT, content="Hello")
        event = StreamEvent(
            type=StreamEventType.AGENT_OUTPUT,
            agent_id="test-id",
            chunk=chunk,
        )
        assert event.type == StreamEventType.AGENT_OUTPUT
        assert event.chunk.content == "Hello"


class TestClaudeCodeMessage:
    """Tests for ClaudeCodeMessage parsing."""

    def test_parse_system_message(self):
        """Test parsing a system message."""
        line = '{"type": "system", "session_id": "abc123"}'
        msg = ClaudeCodeMessage.from_json_line(line)
        assert msg is not None
        assert msg.type == "system"
        assert msg.session_id == "abc123"

    def test_parse_assistant_message(self):
        """Test parsing an assistant message."""
        line = '{"type": "assistant", "content": [{"type": "text", "text": "Hello!"}]}'
        msg = ClaudeCodeMessage.from_json_line(line)
        assert msg is not None
        assert msg.type == "assistant"
        assert isinstance(msg.content, list)

    def test_parse_tool_use_message(self):
        """Test parsing a tool_use message."""
        line = '{"type": "tool_use", "tool_name": "Read", "tool_input": {"path": "/tmp"}}'
        msg = ClaudeCodeMessage.from_json_line(line)
        assert msg is not None
        assert msg.type == "tool_use"
        assert msg.tool_name == "Read"

    def test_parse_result_message(self):
        """Test parsing a result message."""
        line = '{"type": "result", "cost_usd": 0.01, "num_turns": 5}'
        msg = ClaudeCodeMessage.from_json_line(line)
        assert msg is not None
        assert msg.type == "result"
        assert msg.cost_usd == 0.01
        assert msg.num_turns == 5

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON returns None."""
        msg = ClaudeCodeMessage.from_json_line("not json")
        assert msg is None

    def test_parse_empty_line(self):
        """Test parsing empty line returns None."""
        msg = ClaudeCodeMessage.from_json_line("")
        assert msg is None

    def test_to_output_chunk_assistant(self):
        """Test converting assistant message to OutputChunk."""
        line = '{"type": "assistant", "content": [{"type": "text", "text": "Hello!"}]}'
        msg = ClaudeCodeMessage.from_json_line(line)
        chunk = msg.to_output_chunk(sequence=1)
        assert chunk.type == OutputType.ASSISTANT
        assert chunk.content == "Hello!"
        assert chunk.sequence == 1

    def test_to_output_chunk_tool_use(self):
        """Test converting tool_use message to OutputChunk."""
        line = '{"type": "tool_use", "tool_name": "Read", "tool_input": {"path": "/tmp"}}'
        msg = ClaudeCodeMessage.from_json_line(line)
        chunk = msg.to_output_chunk()
        assert chunk.type == OutputType.TOOL_USE
        assert chunk.tool_name == "Read"


class TestSessionModels:
    """Tests for session-related models."""

    def test_session_status_values(self):
        """Test SessionStatus enum values."""
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.PAUSED.value == "paused"
        assert SessionStatus.COMPLETED.value == "completed"

    def test_session_metadata_defaults(self):
        """Test SessionMetadata default values."""
        meta = SessionMetadata(backend=AgentBackendType.CLAUDE_CODE)
        assert meta.id is not None
        assert meta.backend == AgentBackendType.CLAUDE_CODE
        assert meta.total_turns == 0
        assert meta.total_cost_usd == 0.0

    def test_session_state(self):
        """Test SessionState model."""
        meta = SessionMetadata(backend=AgentBackendType.CLAUDE_CODE)
        state = SessionState(metadata=meta)
        assert state.status == SessionStatus.ACTIVE
        assert len(state.agent_runs) == 0

    def test_session_state_touch(self):
        """Test SessionState.touch() updates timestamp."""
        meta = SessionMetadata(backend=AgentBackendType.CLAUDE_CODE)
        state = SessionState(metadata=meta)
        old_updated = state.metadata.updated_at
        state.touch()
        # Timestamp should be same or later
        assert state.metadata.updated_at >= old_updated
