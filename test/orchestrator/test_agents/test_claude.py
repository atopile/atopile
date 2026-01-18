"""Tests for the Claude Code backend."""

from __future__ import annotations

import pytest

from tools.orchestrator.agents.claude import ClaudeCodeBackend
from tools.orchestrator.models import (
    AgentBackendType,
    AgentConfig,
    OutputChunk,
    OutputType,
)


class TestClaudeCodeBackend:
    """Tests for ClaudeCodeBackend."""

    @pytest.fixture
    def backend(self) -> ClaudeCodeBackend:
        """Create a Claude Code backend."""
        return ClaudeCodeBackend()

    def test_backend_type(self, backend: ClaudeCodeBackend):
        """Test backend type is correct."""
        assert backend.backend_type == AgentBackendType.CLAUDE_CODE

    def test_binary_name(self, backend: ClaudeCodeBackend):
        """Test binary name is correct."""
        assert backend.binary_name == "claude"

    def test_capabilities(self, backend: ClaudeCodeBackend):
        """Test backend capabilities."""
        caps = backend.get_capabilities()
        assert caps.streaming is True
        assert caps.resume is True
        assert caps.session_persistence is True
        assert caps.tools is True
        assert caps.budget_control is True
        assert caps.max_turns is True
        assert caps.input_during_run is False  # Claude doesn't support stdin during run


class TestClaudeCodeCommandBuilding:
    """Tests for Claude Code command building."""

    @pytest.fixture
    def backend(self) -> ClaudeCodeBackend:
        """Create a Claude Code backend."""
        return ClaudeCodeBackend()

    def test_build_basic_command(self, backend: ClaudeCodeBackend):
        """Test building a basic command."""
        if not backend.is_available():
            pytest.skip("Claude Code not available")

        config = AgentConfig(prompt="What is 2+2?")
        cmd = backend.build_command(config)

        assert len(cmd) >= 5
        assert cmd[0].endswith("claude")
        assert "-p" in cmd
        assert "What is 2+2?" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd

    def test_build_command_with_max_turns(self, backend: ClaudeCodeBackend):
        """Test building command with max turns."""
        if not backend.is_available():
            pytest.skip("Claude Code not available")

        config = AgentConfig(prompt="test", max_turns=5)
        cmd = backend.build_command(config)

        assert "--max-turns" in cmd
        idx = cmd.index("--max-turns")
        assert cmd[idx + 1] == "5"

    def test_build_command_with_budget(self, backend: ClaudeCodeBackend):
        """Test building command with budget limit."""
        if not backend.is_available():
            pytest.skip("Claude Code not available")

        config = AgentConfig(prompt="test", max_budget_usd=1.5)
        cmd = backend.build_command(config)

        assert "--max-budget-usd" in cmd
        idx = cmd.index("--max-budget-usd")
        assert cmd[idx + 1] == "1.5"

    def test_build_command_with_session_resume(self, backend: ClaudeCodeBackend):
        """Test building command with session resumption."""
        if not backend.is_available():
            pytest.skip("Claude Code not available")

        config = AgentConfig(
            prompt="continue",
            session_id="session-123",
            resume_session=True,
        )
        cmd = backend.build_command(config)

        assert "--resume" in cmd
        assert "session-123" in cmd

    def test_build_command_with_allowed_tools(self, backend: ClaudeCodeBackend):
        """Test building command with allowed tools."""
        if not backend.is_available():
            pytest.skip("Claude Code not available")

        config = AgentConfig(
            prompt="test",
            allowed_tools=["Read", "Write", "Glob"],
        )
        cmd = backend.build_command(config)

        assert "--allowedTools" in cmd
        idx = cmd.index("--allowedTools")
        assert cmd[idx + 1] == "Read,Write,Glob"

    def test_build_command_with_disallowed_tools(self, backend: ClaudeCodeBackend):
        """Test building command with disallowed tools."""
        if not backend.is_available():
            pytest.skip("Claude Code not available")

        config = AgentConfig(
            prompt="test",
            disallowed_tools=["Bash"],
        )
        cmd = backend.build_command(config)

        assert "--disallowedTools" in cmd
        idx = cmd.index("--disallowedTools")
        assert cmd[idx + 1] == "Bash"

    def test_build_command_with_model(self, backend: ClaudeCodeBackend):
        """Test building command with model selection."""
        if not backend.is_available():
            pytest.skip("Claude Code not available")

        config = AgentConfig(prompt="test", model="opus")
        cmd = backend.build_command(config)

        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "opus"

    def test_build_command_with_system_prompt(self, backend: ClaudeCodeBackend):
        """Test building command with system prompt."""
        if not backend.is_available():
            pytest.skip("Claude Code not available")

        config = AgentConfig(prompt="test", system_prompt="Be helpful")
        cmd = backend.build_command(config)

        assert "--system-prompt" in cmd
        idx = cmd.index("--system-prompt")
        assert cmd[idx + 1] == "Be helpful"


class TestClaudeCodeOutputParsing:
    """Tests for Claude Code output parsing."""

    @pytest.fixture
    def backend(self) -> ClaudeCodeBackend:
        """Create a Claude Code backend."""
        return ClaudeCodeBackend()

    def test_parse_system_line(self, backend: ClaudeCodeBackend):
        """Test parsing a system message line."""
        line = '{"type": "system", "session_id": "abc123"}'
        chunk = backend.parse_output_line(line, 1)

        assert chunk is not None
        assert chunk.type == OutputType.SYSTEM
        assert chunk.sequence == 1

    def test_parse_assistant_line(self, backend: ClaudeCodeBackend):
        """Test parsing an assistant message line."""
        line = '{"type": "assistant", "content": [{"type": "text", "text": "Hello!"}]}'
        chunk = backend.parse_output_line(line, 2)

        assert chunk is not None
        assert chunk.type == OutputType.ASSISTANT
        assert chunk.content == "Hello!"
        assert chunk.sequence == 2

    def test_parse_tool_use_line(self, backend: ClaudeCodeBackend):
        """Test parsing a tool_use line."""
        line = '{"type": "tool_use", "tool_name": "Read", "tool_input": {"path": "/tmp"}}'
        chunk = backend.parse_output_line(line, 3)

        assert chunk is not None
        assert chunk.type == OutputType.TOOL_USE
        assert chunk.tool_name == "Read"

    def test_parse_result_line(self, backend: ClaudeCodeBackend):
        """Test parsing a result line."""
        line = '{"type": "result", "cost_usd": 0.01}'
        chunk = backend.parse_output_line(line, 4)

        assert chunk is not None
        assert chunk.type == OutputType.RESULT

    def test_parse_empty_line(self, backend: ClaudeCodeBackend):
        """Test parsing an empty line returns None."""
        chunk = backend.parse_output_line("", 0)
        assert chunk is None

    def test_parse_invalid_json(self, backend: ClaudeCodeBackend):
        """Test parsing invalid JSON returns RAW chunk."""
        chunk = backend.parse_output_line("not json", 0)
        assert chunk is not None
        assert chunk.type == OutputType.RAW
        assert chunk.content == "not json"

    def test_parse_preserves_raw_line(self, backend: ClaudeCodeBackend):
        """Test that parsing preserves the raw line."""
        line = '{"type": "system"}'
        chunk = backend.parse_output_line(line, 0)
        assert chunk.raw_line == line


class TestClaudeCodeSessionExtraction:
    """Tests for session ID extraction."""

    @pytest.fixture
    def backend(self) -> ClaudeCodeBackend:
        """Create a Claude Code backend."""
        return ClaudeCodeBackend()

    def test_extract_session_id(self, backend: ClaudeCodeBackend):
        """Test extracting session ID from chunk."""
        chunk = OutputChunk(
            type=OutputType.SYSTEM,
            data={"session_id": "abc123", "type": "system"},
        )
        session_id = backend.extract_session_id(chunk)
        assert session_id == "abc123"

    def test_extract_session_id_missing(self, backend: ClaudeCodeBackend):
        """Test extracting session ID when not present."""
        chunk = OutputChunk(
            type=OutputType.ASSISTANT,
            data={"type": "assistant"},
        )
        session_id = backend.extract_session_id(chunk)
        assert session_id is None

    def test_extract_session_id_no_data(self, backend: ClaudeCodeBackend):
        """Test extracting session ID when no data."""
        chunk = OutputChunk(type=OutputType.RAW, content="test")
        session_id = backend.extract_session_id(chunk)
        assert session_id is None

    def test_get_resume_args(self, backend: ClaudeCodeBackend):
        """Test getting resume arguments."""
        args = backend.get_resume_args("session-123")
        assert args == ["--resume", "session-123"]
