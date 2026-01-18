"""Tests for process management."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.orchestrator import AgentConfig, AgentState, AgentStatus, ProcessManager
from tools.orchestrator.agents import ClaudeCodeBackend
from tools.orchestrator.core.process import ManagedProcess
from tools.orchestrator.exceptions import AgentNotFoundError, AgentNotRunningError
from tools.orchestrator.models import AgentBackendType, OutputChunk, OutputType


class TestProcessManagerBasics:
    """Basic tests for ProcessManager."""

    @pytest.fixture
    def process_manager(self, temp_storage_dir: Path) -> ProcessManager:
        """Create a process manager."""
        pm = ProcessManager()
        yield pm
        pm.cleanup_all()

    def test_create_process_manager(self):
        """Test creating a process manager."""
        pm = ProcessManager()
        assert pm is not None
        pm.cleanup_all()

    def test_create_with_callbacks(self):
        """Test creating a process manager with callbacks."""
        output_callback = MagicMock()
        status_callback = MagicMock()

        pm = ProcessManager(
            on_output=output_callback,
            on_status_change=status_callback,
        )
        assert pm._on_output is output_callback
        assert pm._on_status_change is status_callback
        pm.cleanup_all()

    def test_list_running_empty(self, process_manager: ProcessManager):
        """Test listing running processes when empty."""
        running = process_manager.list_running()
        assert running == []

    def test_poll_all_empty(self, process_manager: ProcessManager):
        """Test polling all processes when empty."""
        result = process_manager.poll_all()
        assert result == {}

    def test_get_process_not_found(self, process_manager: ProcessManager):
        """Test getting a process that doesn't exist."""
        managed = process_manager.get_process("nonexistent")
        assert managed is None

    def test_is_running_not_found(self, process_manager: ProcessManager):
        """Test is_running for a process that doesn't exist."""
        assert process_manager.is_running("nonexistent") is False

    def test_get_exit_code_not_found(self, process_manager: ProcessManager):
        """Test get_exit_code for a process that doesn't exist."""
        assert process_manager.get_exit_code("nonexistent") is None

    def test_terminate_not_found(self, process_manager: ProcessManager):
        """Test terminating a process that doesn't exist."""
        with pytest.raises(AgentNotFoundError):
            process_manager.terminate("nonexistent")

    def test_kill_not_found(self, process_manager: ProcessManager):
        """Test killing a process that doesn't exist."""
        with pytest.raises(AgentNotFoundError):
            process_manager.kill("nonexistent")

    def test_send_input_not_found(self, process_manager: ProcessManager):
        """Test sending input to a process that doesn't exist."""
        with pytest.raises(AgentNotFoundError):
            process_manager.send_input("nonexistent", "test")

    def test_get_output_not_found(self, process_manager: ProcessManager):
        """Test getting output for a process that doesn't exist."""
        chunks = process_manager.get_output("nonexistent")
        assert chunks == []

    def test_cleanup_not_found(self, process_manager: ProcessManager):
        """Test cleaning up a process that doesn't exist."""
        # Should not raise
        process_manager.cleanup("nonexistent")


class TestMockedProcessSpawning:
    """Tests for process spawning with mocked subprocess."""

    @pytest.fixture
    def mock_backend(self):
        """Create a mock backend."""
        backend = MagicMock(spec=ClaudeCodeBackend)
        backend.backend_type = AgentBackendType.CLAUDE_CODE
        backend.binary_name = "claude"
        backend.is_available.return_value = True
        backend.get_binary_path.return_value = Path("/bin/echo")
        backend.build_command.return_value = ["/bin/echo", "hello"]
        backend.parse_output_line.return_value = OutputChunk(
            type=OutputType.RAW,
            content="hello",
            sequence=1,
        )
        backend.extract_session_id.return_value = None
        return backend

    @pytest.fixture
    def process_manager(self, temp_storage_dir: Path) -> ProcessManager:
        """Create a process manager."""
        pm = ProcessManager()
        yield pm
        pm.cleanup_all()

    def test_spawn_with_echo(
        self, process_manager: ProcessManager, mock_backend, temp_storage_dir: Path
    ):
        """Test spawning a process using echo command."""
        config = AgentConfig(
            backend=AgentBackendType.CLAUDE_CODE,
            prompt="test",
        )
        agent = AgentState(config=config, status=AgentStatus.PENDING)

        # Patch get_backend to return our mock
        with patch(
            "tools.orchestrator.core.process.get_backend"
        ) as mock_get_backend:
            mock_get_backend.return_value = mock_backend

            managed = process_manager.spawn(agent)

            assert managed is not None
            assert managed.agent_id == agent.id
            assert managed.process is not None

            # Wait for process to complete
            exit_code = managed.process.wait(timeout=5)
            assert exit_code == 0

    def test_spawn_captures_pid(
        self, process_manager: ProcessManager, mock_backend, temp_storage_dir: Path
    ):
        """Test that spawn captures the process PID."""
        config = AgentConfig(
            backend=AgentBackendType.CLAUDE_CODE,
            prompt="test",
        )
        agent = AgentState(config=config, status=AgentStatus.PENDING)

        with patch(
            "tools.orchestrator.core.process.get_backend"
        ) as mock_get_backend:
            mock_get_backend.return_value = mock_backend

            managed = process_manager.spawn(agent)

            assert managed.process.pid is not None
            assert managed.process.pid > 0

            # Wait for completion
            managed.process.wait(timeout=5)

    def test_get_process_after_spawn(
        self, process_manager: ProcessManager, mock_backend, temp_storage_dir: Path
    ):
        """Test getting a process after spawning."""
        config = AgentConfig(
            backend=AgentBackendType.CLAUDE_CODE,
            prompt="test",
        )
        agent = AgentState(config=config, status=AgentStatus.PENDING)

        with patch(
            "tools.orchestrator.core.process.get_backend"
        ) as mock_get_backend:
            mock_get_backend.return_value = mock_backend

            process_manager.spawn(agent)

            retrieved = process_manager.get_process(agent.id)
            assert retrieved is not None
            assert retrieved.agent_id == agent.id

            # Wait for completion
            retrieved.process.wait(timeout=5)


class TestOutputBuffering:
    """Tests for output buffering and streaming."""

    @pytest.fixture
    def process_manager(self, temp_storage_dir: Path) -> ProcessManager:
        """Create a process manager."""
        pm = ProcessManager(max_buffer_size=100)
        yield pm
        pm.cleanup_all()

    def test_buffer_max_size(self):
        """Test that buffer respects max size."""
        from collections import deque

        buffer = deque(maxlen=5)
        for i in range(10):
            buffer.append(i)

        assert len(buffer) == 5
        assert list(buffer) == [5, 6, 7, 8, 9]

    def test_managed_process_buffer_initialization(self):
        """Test that ManagedProcess initializes buffer correctly."""
        from collections import deque

        managed = ManagedProcess(
            agent_id="test",
            process=MagicMock(),
            backend=MagicMock(),
            config=MagicMock(),
            output_buffer=deque(maxlen=100),
        )

        assert len(managed.output_buffer) == 0
        assert managed.output_buffer.maxlen == 100


class TestProcessLifecycle:
    """Tests for process lifecycle management."""

    @pytest.fixture
    def mock_backend_for_lifecycle(self):
        """Create a mock backend for lifecycle tests."""
        backend = MagicMock(spec=ClaudeCodeBackend)
        backend.backend_type = AgentBackendType.CLAUDE_CODE
        backend.binary_name = "sleep"
        backend.is_available.return_value = True
        backend.get_binary_path.return_value = Path("/bin/sleep")
        backend.build_command.return_value = ["/bin/sleep", "30"]
        backend.parse_output_line.return_value = None
        backend.extract_session_id.return_value = None
        return backend

    @pytest.fixture
    def process_manager(self, temp_storage_dir: Path) -> ProcessManager:
        """Create a process manager."""
        pm = ProcessManager()
        yield pm
        pm.cleanup_all()

    def test_terminate_running_process(
        self, process_manager: ProcessManager, mock_backend_for_lifecycle, temp_storage_dir: Path
    ):
        """Test terminating a running process."""
        config = AgentConfig(
            backend=AgentBackendType.CLAUDE_CODE,
            prompt="test",
        )
        agent = AgentState(config=config, status=AgentStatus.PENDING)

        with patch(
            "tools.orchestrator.core.process.get_backend"
        ) as mock_get_backend:
            mock_get_backend.return_value = mock_backend_for_lifecycle

            managed = process_manager.spawn(agent)

            # Process should be running
            assert managed.process.poll() is None

            # Terminate
            result = process_manager.terminate(agent.id, timeout=2.0)
            assert result is True

            # Process should be terminated
            assert managed.process.poll() is not None

    def test_kill_running_process(
        self, process_manager: ProcessManager, mock_backend_for_lifecycle, temp_storage_dir: Path
    ):
        """Test killing a running process."""
        config = AgentConfig(
            backend=AgentBackendType.CLAUDE_CODE,
            prompt="test",
        )
        agent = AgentState(config=config, status=AgentStatus.PENDING)

        with patch(
            "tools.orchestrator.core.process.get_backend"
        ) as mock_get_backend:
            mock_get_backend.return_value = mock_backend_for_lifecycle

            managed = process_manager.spawn(agent)

            # Process should be running
            assert managed.process.poll() is None

            # Kill
            result = process_manager.kill(agent.id)
            assert result is True

            # Process should be terminated
            assert managed.process.poll() is not None

    def test_is_running_returns_correct_status(
        self, process_manager: ProcessManager, mock_backend_for_lifecycle, temp_storage_dir: Path
    ):
        """Test that is_running returns correct status."""
        config = AgentConfig(
            backend=AgentBackendType.CLAUDE_CODE,
            prompt="test",
        )
        agent = AgentState(config=config, status=AgentStatus.PENDING)

        with patch(
            "tools.orchestrator.core.process.get_backend"
        ) as mock_get_backend:
            mock_get_backend.return_value = mock_backend_for_lifecycle

            process_manager.spawn(agent)

            # Should be running
            assert process_manager.is_running(agent.id) is True

            # Terminate
            process_manager.terminate(agent.id, timeout=2.0)

            # Should not be running
            assert process_manager.is_running(agent.id) is False

    def test_poll_all_returns_exit_codes(
        self, process_manager: ProcessManager, mock_backend_for_lifecycle, temp_storage_dir: Path
    ):
        """Test that poll_all returns correct exit codes."""
        config = AgentConfig(
            backend=AgentBackendType.CLAUDE_CODE,
            prompt="test",
        )
        agent = AgentState(config=config, status=AgentStatus.PENDING)

        with patch(
            "tools.orchestrator.core.process.get_backend"
        ) as mock_get_backend:
            mock_get_backend.return_value = mock_backend_for_lifecycle

            process_manager.spawn(agent)

            # Should be running (poll returns None)
            result = process_manager.poll_all()
            assert agent.id in result
            assert result[agent.id] is None

            # Terminate
            process_manager.terminate(agent.id, timeout=2.0)

            # Should have exit code
            result = process_manager.poll_all()
            assert agent.id in result
            # SIGTERM typically results in exit code -15 or 143
            assert result[agent.id] is not None

    def test_cleanup_closes_resources(
        self, process_manager: ProcessManager, mock_backend_for_lifecycle, temp_storage_dir: Path
    ):
        """Test that cleanup closes resources properly."""
        config = AgentConfig(
            backend=AgentBackendType.CLAUDE_CODE,
            prompt="test",
        )
        agent = AgentState(config=config, status=AgentStatus.PENDING)

        with patch(
            "tools.orchestrator.core.process.get_backend"
        ) as mock_get_backend:
            mock_get_backend.return_value = mock_backend_for_lifecycle

            process_manager.spawn(agent)
            process_manager.terminate(agent.id, timeout=2.0)
            process_manager.cleanup(agent.id)

            # Process should be removed from manager
            assert process_manager.get_process(agent.id) is None


class TestManagedProcessDataclass:
    """Tests for the ManagedProcess dataclass."""

    def test_managed_process_fields(self):
        """Test ManagedProcess has required fields."""
        from collections import deque
        import queue

        managed = ManagedProcess(
            agent_id="test-id",
            process=MagicMock(),
            backend=MagicMock(),
            config=MagicMock(),
        )

        assert managed.agent_id == "test-id"
        assert managed.log_file is None
        assert managed.stdout_thread is None
        assert managed.stderr_thread is None
        assert isinstance(managed.output_buffer, deque)
        assert isinstance(managed.output_queue, queue.Queue)
        assert managed.sequence_counter == 0
        assert managed.session_id is None

    def test_managed_process_lock(self):
        """Test ManagedProcess has a lock for thread safety."""
        import threading

        managed = ManagedProcess(
            agent_id="test-id",
            process=MagicMock(),
            backend=MagicMock(),
            config=MagicMock(),
        )

        assert isinstance(managed._lock, threading.Lock)
