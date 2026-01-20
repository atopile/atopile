"""Unit tests for CodexBackend."""

import pytest

from orchestrator.agents.codex import CodexBackend
from orchestrator.models import AgentBackendType, AgentConfig, OutputType


@pytest.fixture
def backend():
    """Create a CodexBackend instance."""
    return CodexBackend()


class TestCodexBackendProperties:
    """Test backend properties."""

    def test_backend_type(self, backend):
        """Backend type should be CODEX."""
        assert backend.backend_type == AgentBackendType.CODEX

    def test_binary_name(self, backend):
        """Binary name should be 'codex'."""
        assert backend.binary_name == "codex"


class TestCodexBackendCapabilities:
    """Test backend capabilities."""

    def test_capabilities(self, backend):
        """Test reported capabilities."""
        caps = backend.get_capabilities()

        assert caps.streaming is True
        assert caps.resume is True
        assert caps.session_persistence is True
        assert caps.input_during_run is False
        assert caps.tools is True
        assert caps.budget_control is False
        assert caps.max_turns is False
        assert caps.allowed_tools is False


class TestCodexBackendBuildCommand:
    """Test command building."""

    def test_basic_command(self, backend, monkeypatch):
        """Test basic command without options."""
        monkeypatch.setattr(backend, "get_binary_path", lambda: "/usr/local/bin/codex")

        config = AgentConfig(
            backend=AgentBackendType.CODEX,
            prompt="hello world",
        )

        cmd = backend.build_command(config)

        assert cmd[0] == "/usr/local/bin/codex"
        assert "exec" in cmd
        assert "--json" in cmd
        assert "--dangerously-bypass-approvals-and-sandbox" in cmd
        assert "--skip-git-repo-check" in cmd
        assert "hello world" in cmd

    def test_command_with_model(self, backend, monkeypatch):
        """Test command with model specified."""
        monkeypatch.setattr(backend, "get_binary_path", lambda: "/usr/local/bin/codex")

        config = AgentConfig(
            backend=AgentBackendType.CODEX,
            prompt="hello",
            model="gpt-4o",
        )

        cmd = backend.build_command(config)

        assert "-m" in cmd
        assert "gpt-4o" in cmd

    def test_command_with_working_directory(self, backend, monkeypatch):
        """Test command with working directory."""
        monkeypatch.setattr(backend, "get_binary_path", lambda: "/usr/local/bin/codex")

        config = AgentConfig(
            backend=AgentBackendType.CODEX,
            prompt="hello",
            working_directory="/tmp/test",
        )

        cmd = backend.build_command(config)

        assert "-C" in cmd
        assert "/tmp/test" in cmd

    def test_resume_command(self, backend, monkeypatch):
        """Test resume command uses subcommand pattern."""
        monkeypatch.setattr(backend, "get_binary_path", lambda: "/usr/local/bin/codex")

        config = AgentConfig(
            backend=AgentBackendType.CODEX,
            prompt="continue",
            session_id="abc-123",
            resume_session=True,
        )

        cmd = backend.build_command(config)

        # Verify resume is a subcommand, not a flag
        assert "resume" in cmd
        assert "abc-123" in cmd
        # resume should come after exec
        exec_idx = cmd.index("exec")
        resume_idx = cmd.index("resume")
        assert resume_idx == exec_idx + 1

    def test_command_without_binary(self, backend, monkeypatch):
        """Test that missing binary raises RuntimeError."""
        monkeypatch.setattr(backend, "get_binary_path", lambda: None)

        config = AgentConfig(
            backend=AgentBackendType.CODEX,
            prompt="hello",
        )

        with pytest.raises(RuntimeError, match="Codex binary not found"):
            backend.build_command(config)


class TestCodexBackendParseOutput:
    """Test output line parsing."""

    def test_parse_thread_started(self, backend):
        """Test parsing thread.started event."""
        line = '{"type":"thread.started","thread_id":"abc-123"}'

        chunk = backend.parse_output_line(line, sequence=1)

        assert chunk is not None
        assert chunk.type == OutputType.INIT
        assert chunk.data["thread_id"] == "abc-123"
        assert chunk.sequence == 1

    def test_parse_turn_started(self, backend):
        """Test parsing turn.started event."""
        line = '{"type":"turn.started"}'

        chunk = backend.parse_output_line(line, sequence=2)

        assert chunk is not None
        assert chunk.type == OutputType.STREAM_START

    def test_parse_turn_completed(self, backend):
        """Test parsing turn.completed event."""
        line = '{"type":"turn.completed","usage":{"input_tokens":100}}'

        chunk = backend.parse_output_line(line, sequence=3)

        assert chunk is not None
        assert chunk.type == OutputType.RESULT

    def test_parse_turn_failed(self, backend):
        """Test parsing turn.failed event."""
        line = '{"type":"turn.failed","error":{"message":"Something went wrong"}}'

        chunk = backend.parse_output_line(line, sequence=4)

        assert chunk is not None
        assert chunk.type == OutputType.ERROR
        assert chunk.content == "Something went wrong"

    def test_parse_error(self, backend):
        """Test parsing error event."""
        line = '{"type":"error","message":"API error"}'

        chunk = backend.parse_output_line(line, sequence=5)

        assert chunk is not None
        assert chunk.type == OutputType.ERROR
        assert chunk.content == "API error"

    def test_parse_agent_message(self, backend):
        """Test parsing item.completed with agent_message."""
        line = '{"type":"item.completed","item":{"type":"agent_message","text":"Hello!"}}'

        chunk = backend.parse_output_line(line, sequence=6)

        assert chunk is not None
        assert chunk.type == OutputType.ASSISTANT
        assert chunk.content == "Hello!"

    def test_parse_reasoning(self, backend):
        """Test parsing item.completed with reasoning."""
        line = '{"type":"item.completed","item":{"type":"reasoning","text":"Thinking..."}}'

        chunk = backend.parse_output_line(line, sequence=7)

        assert chunk is not None
        assert chunk.type == OutputType.ASSISTANT
        assert chunk.content == "Thinking..."

    def test_parse_command_started(self, backend):
        """Test parsing item.started with command_execution."""
        line = '{"type":"item.started","item":{"type":"command_execution","command":"ls -la"}}'

        chunk = backend.parse_output_line(line, sequence=8)

        assert chunk is not None
        assert chunk.type == OutputType.TOOL_USE
        assert chunk.tool_name == "shell"
        assert chunk.tool_input == {"command": "ls -la"}

    def test_parse_command_completed(self, backend):
        """Test parsing item.completed with command_execution."""
        line = '{"type":"item.completed","item":{"type":"command_execution","command":"ls","aggregated_output":"file.txt","exit_code":0}}'

        chunk = backend.parse_output_line(line, sequence=9)

        assert chunk is not None
        assert chunk.type == OutputType.TOOL_RESULT
        assert chunk.tool_name == "shell"
        assert chunk.tool_result == "file.txt"
        assert chunk.is_error is False

    def test_parse_command_completed_with_error(self, backend):
        """Test parsing command_execution with non-zero exit code."""
        line = '{"type":"item.completed","item":{"type":"command_execution","command":"false","aggregated_output":"","exit_code":1}}'

        chunk = backend.parse_output_line(line, sequence=10)

        assert chunk is not None
        assert chunk.type == OutputType.TOOL_RESULT
        assert chunk.is_error is True

    def test_parse_unknown_event(self, backend):
        """Test parsing unknown event type returns raw."""
        line = '{"type":"unknown_event","data":"something"}'

        chunk = backend.parse_output_line(line, sequence=11)

        assert chunk is not None
        assert chunk.type == OutputType.RAW

    def test_parse_invalid_json(self, backend):
        """Test parsing invalid JSON returns raw."""
        line = "not valid json {"

        chunk = backend.parse_output_line(line, sequence=12)

        assert chunk is not None
        assert chunk.type == OutputType.RAW
        assert chunk.content == line

    def test_parse_empty_line(self, backend):
        """Test parsing empty line returns None."""
        chunk = backend.parse_output_line("", sequence=13)
        assert chunk is None

        chunk = backend.parse_output_line("   ", sequence=14)
        assert chunk is None


class TestCodexBackendExtractSessionId:
    """Test session ID extraction."""

    def test_extract_session_id_from_thread_started(self, backend):
        """Test extracting thread_id from thread.started event."""
        line = '{"type":"thread.started","thread_id":"abc-123-def"}'
        chunk = backend.parse_output_line(line, sequence=1)

        session_id = backend.extract_session_id(chunk)

        assert session_id == "abc-123-def"

    def test_extract_session_id_no_data(self, backend):
        """Test extracting session ID when no data present."""
        line = "plain text"
        chunk = backend.parse_output_line(line, sequence=1)

        session_id = backend.extract_session_id(chunk)

        assert session_id is None

    def test_extract_session_id_no_thread_id(self, backend):
        """Test extracting session ID when thread_id not present."""
        line = '{"type":"turn.started"}'
        chunk = backend.parse_output_line(line, sequence=1)

        session_id = backend.extract_session_id(chunk)

        assert session_id is None


class TestCodexBackendResumeArgs:
    """Test resume args."""

    def test_get_resume_args_empty(self, backend):
        """Resume args should be empty (handled in build_command)."""
        args = backend.get_resume_args("abc-123")
        assert args == []
