"""Process management for spawning and controlling agents."""

from __future__ import annotations

import logging
import os
import pty
import queue
import subprocess
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, TYPE_CHECKING, Callable

from ..agents import AgentBackend, get_backend
from ..common import get_logs_dir
from ..exceptions import (
    AgentNotFoundError,
    AgentNotRunningError,
    BackendNotAvailableError,
    BackendSpawnError,
)
from ..models import (
    AgentBackendType,
    AgentConfig,
    AgentState,
    AgentStatus,
    OutputChunk,
    OutputType,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ManagedProcess:
    """A managed subprocess with output buffering."""

    agent_id: str
    process: subprocess.Popen
    backend: AgentBackend
    config: AgentConfig
    run_number: int = 0  # The run number for versioned logs
    log_file: Path | None = None
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None
    output_buffer: deque[OutputChunk] = field(
        default_factory=lambda: deque(maxlen=10000)
    )
    output_queue: queue.Queue[OutputChunk] = field(default_factory=queue.Queue)
    sequence_counter: int = 0
    session_id: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _log_handle: IO[str] | None = None
    _pty_master_fd: int | None = None  # PTY master fd for stdin when input_during_run


class ProcessManager:
    """Manages spawning and lifecycle of agent processes.

    Provides:
    - Process spawning with threaded output reading
    - Output buffering and streaming
    - Process monitoring and cleanup
    - Session ID extraction
    """

    def __init__(
        self,
        on_output: Callable[[str, OutputChunk], None] | None = None,
        on_status_change: Callable[[str, AgentStatus], None] | None = None,
        max_buffer_size: int = 10000,
    ) -> None:
        """Initialize the process manager.

        Args:
            on_output: Callback for new output chunks (agent_id, chunk)
            on_status_change: Callback for status changes (agent_id, new_status)
            max_buffer_size: Maximum number of output chunks to buffer
        """
        self._processes: dict[str, ManagedProcess] = {}
        self._lock = threading.RLock()
        self._on_output = on_output
        self._on_status_change = on_status_change
        self._max_buffer_size = max_buffer_size

    def spawn(self, agent_state: AgentState) -> ManagedProcess:
        """Spawn a new agent process.

        Args:
            agent_state: The agent state (must have config and id)

        Returns:
            The managed process

        Raises:
            BackendNotAvailableError: If the backend is not available
            BackendSpawnError: If spawning fails
        """
        config = agent_state.config
        backend = get_backend(config.backend)

        if not backend.is_available():
            raise BackendNotAvailableError(
                str(config.backend),
                f"Binary '{backend.binary_name}' not found in PATH",
            )

        # Build command
        try:
            cmd = backend.build_command(config)
        except Exception as e:
            raise BackendSpawnError(str(config.backend), str(e)) from e

        # Set up environment
        env = os.environ.copy()
        if config.environment:
            env.update(config.environment)

        # Set up working directory
        cwd = config.working_directory or os.getcwd()

        # Get run number for versioned log file
        run_number = agent_state.run_count

        # Set up log file with versioned naming
        log_file = get_logs_dir() / f"agent-{agent_state.id}_run-{run_number}.log"
        log_handle = open(log_file, "w")

        logger.info(f"Spawning agent {agent_state.id}: {' '.join(cmd)}")

        # Check if we need to use a PTY for stdin (for interactive input during run)
        capabilities = backend.get_capabilities()
        pty_master_fd = None
        pty_slave_fd = None

        if capabilities.input_during_run:
            # Use a PTY for stdin - this makes Claude think it's interactive
            # and flushes output properly while still accepting input
            pty_master_fd, pty_slave_fd = pty.openpty()
            stdin_arg = pty_slave_fd
        else:
            stdin_arg = subprocess.PIPE

        try:
            process = subprocess.Popen(
                cmd,
                stdin=stdin_arg,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
                bufsize=1,  # Line buffered
                text=True,
            )
        except Exception as e:
            log_handle.close()
            if pty_master_fd is not None:
                os.close(pty_master_fd)
            if pty_slave_fd is not None:
                os.close(pty_slave_fd)
            raise BackendSpawnError(str(config.backend), str(e)) from e

        # Close slave fd in parent process (child has it)
        if pty_slave_fd is not None:
            os.close(pty_slave_fd)

        managed = ManagedProcess(
            agent_id=agent_state.id,
            process=process,
            backend=backend,
            config=config,
            run_number=run_number,
            log_file=log_file,
            output_buffer=deque(maxlen=self._max_buffer_size),
            _log_handle=log_handle,
            _pty_master_fd=pty_master_fd,
        )

        # Close stdin for backends that don't support input during run
        if not capabilities.input_during_run:
            try:
                process.stdin.close()
            except Exception:
                pass

        # Start output reader threads
        managed.stdout_thread = threading.Thread(
            target=self._read_output,
            args=(managed, process.stdout, False),
            daemon=True,
        )
        managed.stderr_thread = threading.Thread(
            target=self._read_output,
            args=(managed, process.stderr, True),
            daemon=True,
        )

        managed.stdout_thread.start()
        managed.stderr_thread.start()

        with self._lock:
            self._processes[agent_state.id] = managed

        return managed

    def _read_output(
        self,
        managed: ManagedProcess,
        stream,
        is_stderr: bool,
    ) -> None:
        """Read output from a process stream in a thread."""
        try:
            for line in iter(stream.readline, ""):
                if not line:
                    break

                # Write to log file with timestamp prefix for later retrieval
                # Format: ISO_TIMESTAMP|raw_json_line
                if managed._log_handle:
                    try:
                        from datetime import datetime
                        timestamp = datetime.now().isoformat()
                        managed._log_handle.write(f"{timestamp}|{line}")
                        managed._log_handle.flush()
                    except Exception:
                        pass

                # Parse the line
                with managed._lock:
                    managed.sequence_counter += 1
                    seq = managed.sequence_counter

                if is_stderr:
                    chunk = OutputChunk(
                        type=OutputType.ERROR,
                        content=line.rstrip(),
                        raw_line=line,
                        sequence=seq,
                    )
                else:
                    chunk = managed.backend.parse_output_line(line, seq)
                    if chunk is None:
                        continue

                # Extract session ID if present
                session_id = managed.backend.extract_session_id(chunk)
                if session_id:
                    managed.session_id = session_id

                # Add to buffer and queue
                with managed._lock:
                    managed.output_buffer.append(chunk)
                managed.output_queue.put(chunk)

                # Call callback
                if self._on_output:
                    try:
                        self._on_output(managed.agent_id, chunk)
                    except Exception as e:
                        logger.warning(f"Output callback error: {e}")

        except Exception as e:
            logger.warning(f"Error reading output for agent {managed.agent_id}: {e}")
        finally:
            try:
                stream.close()
            except Exception:
                pass

    def get_process(self, agent_id: str) -> ManagedProcess | None:
        """Get a managed process by agent ID."""
        with self._lock:
            return self._processes.get(agent_id)

    def is_running(self, agent_id: str) -> bool:
        """Check if a process is still running."""
        managed = self.get_process(agent_id)
        if managed is None:
            return False
        return managed.process.poll() is None

    def get_exit_code(self, agent_id: str) -> int | None:
        """Get the exit code of a process, or None if still running."""
        managed = self.get_process(agent_id)
        if managed is None:
            return None
        return managed.process.poll()

    def wait_for_output_and_get_session_id(
        self, agent_id: str, timeout: float = 2.0
    ) -> str | None:
        """Wait for output threads to finish and return the session_id.

        This should be called after the process has exited to ensure
        all output has been processed and the session_id has been extracted.

        Args:
            agent_id: The agent ID
            timeout: Max seconds to wait for each thread

        Returns:
            The session ID if found, None otherwise
        """
        managed = self.get_process(agent_id)
        if managed is None:
            return None

        # Wait for output threads to finish processing
        if managed.stdout_thread and managed.stdout_thread.is_alive():
            managed.stdout_thread.join(timeout=timeout)
        if managed.stderr_thread and managed.stderr_thread.is_alive():
            managed.stderr_thread.join(timeout=timeout)

        return managed.session_id

    def terminate(self, agent_id: str, timeout: float = 5.0) -> bool:
        """Gracefully terminate a process.

        Args:
            agent_id: The agent ID
            timeout: Seconds to wait before force-killing

        Returns:
            True if terminated, False if not found

        Raises:
            AgentNotRunningError: If the agent is not running
        """
        managed = self.get_process(agent_id)
        if managed is None:
            raise AgentNotFoundError(agent_id)

        if managed.process.poll() is not None:
            # Already terminated
            return True

        logger.info(f"Terminating agent {agent_id}")
        managed.process.terminate()

        try:
            managed.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.warning(f"Force killing agent {agent_id}")
            managed.process.kill()
            managed.process.wait(timeout=1.0)

        return True

    def kill(self, agent_id: str) -> bool:
        """Force kill a process immediately.

        Returns:
            True if killed, False if not found
        """
        managed = self.get_process(agent_id)
        if managed is None:
            raise AgentNotFoundError(agent_id)

        if managed.process.poll() is not None:
            return True

        logger.info(f"Killing agent {agent_id}")
        managed.process.kill()
        managed.process.wait(timeout=1.0)
        return True

    def send_input(self, agent_id: str, text: str, newline: bool = True) -> bool:
        """Send input to a process stdin.

        Args:
            agent_id: The agent ID
            text: Text to send
            newline: Whether to append a newline

        Returns:
            True if sent successfully

        Raises:
            AgentNotFoundError: If agent not found
            AgentNotRunningError: If agent not running
        """
        managed = self.get_process(agent_id)
        if managed is None:
            raise AgentNotFoundError(agent_id)

        if managed.process.poll() is not None:
            raise AgentNotRunningError(agent_id)

        # Check if we have a PTY master fd (for input_during_run backends)
        if managed._pty_master_fd is not None:
            try:
                if newline and not text.endswith("\n"):
                    text = text + "\n"
                os.write(managed._pty_master_fd, text.encode())
                return True
            except Exception as e:
                logger.warning(f"Failed to send input to agent {agent_id} via PTY: {e}")
                return False

        # Fall back to stdin pipe
        if managed.process.stdin is None:
            raise AgentNotRunningError(agent_id)

        try:
            if newline and not text.endswith("\n"):
                text = text + "\n"
            managed.process.stdin.write(text)
            managed.process.stdin.flush()
            return True
        except Exception as e:
            logger.warning(f"Failed to send input to agent {agent_id}: {e}")
            return False

    def get_output(
        self,
        agent_id: str,
        since_sequence: int = 0,
        max_chunks: int | None = None,
        backend_type: AgentBackendType | None = None,
    ) -> list[OutputChunk]:
        """Get buffered output chunks.

        Args:
            agent_id: The agent ID
            since_sequence: Only return chunks after this sequence number
            max_chunks: Maximum number of chunks to return
            backend_type: The backend type to use for parsing log files

        Returns:
            List of output chunks
        """
        managed = self.get_process(agent_id)
        if managed is not None:
            # Process is still in memory, use buffer
            with managed._lock:
                chunks = [c for c in managed.output_buffer if c.sequence > since_sequence]
        else:
            # Process was cleaned up, try to read from log file
            chunks = self._read_output_from_log(agent_id, since_sequence, backend_type=backend_type)

        if max_chunks is not None:
            chunks = chunks[:max_chunks]

        return chunks

    def _read_log_file(
        self,
        log_file: Path,
        since_sequence: int = 0,
        backend_type: AgentBackendType | None = None,
    ) -> list[OutputChunk]:
        """Read output chunks from a specific log file.

        Args:
            log_file: Path to the log file
            since_sequence: Only return chunks after this sequence number
            backend_type: The backend type to use for parsing (defaults to Claude Code)

        Returns:
            List of output chunks
        """
        from datetime import datetime

        if not log_file.exists():
            return []

        chunks = []
        try:
            # Use the specified backend for parsing, default to Claude Code
            backend = get_backend(backend_type or AgentBackendType.CLAUDE_CODE)

            with open(log_file, "r") as f:
                for seq, line in enumerate(f, start=1):
                    if seq <= since_sequence:
                        continue
                    line = line.strip()
                    if not line:
                        continue

                    # Check for timestamp prefix (format: ISO_TIMESTAMP|json_data)
                    timestamp = None
                    json_line = line
                    if "|" in line:
                        parts = line.split("|", 1)
                        if len(parts) == 2:
                            try:
                                # Try to parse as ISO timestamp
                                timestamp = datetime.fromisoformat(parts[0])
                                json_line = parts[1]
                            except ValueError:
                                # Not a timestamp prefix, use full line
                                json_line = line

                    chunk = backend.parse_output_line(json_line, seq)
                    if chunk is not None:
                        # Override timestamp if we extracted one from the log
                        if timestamp is not None:
                            chunk.timestamp = timestamp
                        chunks.append(chunk)
        except Exception as e:
            logger.warning(f"Failed to read log file {log_file}: {e}")

        return chunks

    def _read_output_from_log(
        self,
        agent_id: str,
        since_sequence: int = 0,
        run_number: int | None = None,
        backend_type: AgentBackendType | None = None,
    ) -> list[OutputChunk]:
        """Read output chunks from the log file for a completed agent.

        Args:
            agent_id: The agent ID
            since_sequence: Only return chunks after this sequence number
            run_number: Specific run number to read from, or None for latest
            backend_type: The backend type to use for parsing

        Returns:
            List of output chunks
        """
        logs_dir = get_logs_dir()

        # Find the log file - try versioned path first, then legacy
        if run_number is not None:
            log_file = logs_dir / f"agent-{agent_id}_run-{run_number}.log"
        else:
            # Find the latest run's log file
            run_files = sorted(logs_dir.glob(f"agent-{agent_id}_run-*.log"))
            if run_files:
                log_file = run_files[-1]  # Latest run
            else:
                # Fall back to legacy naming
                log_file = logs_dir / f"agent-{agent_id}.log"

        return self._read_log_file(log_file, since_sequence, backend_type)

    def get_all_run_logs(
        self,
        agent_id: str,
        backend_type: AgentBackendType | None = None,
    ) -> list[tuple[int, list[OutputChunk]]]:
        """Get output from all runs of an agent.

        Args:
            agent_id: The agent ID
            backend_type: The backend type to use for parsing

        Returns:
            List of (run_number, chunks) tuples sorted by run number
        """
        logs_dir = get_logs_dir()
        results = []

        # Find all versioned log files for this agent
        run_files = sorted(logs_dir.glob(f"agent-{agent_id}_run-*.log"))

        # Check for legacy log file (original run 0 before versioned logging)
        legacy_file = logs_dir / f"agent-{agent_id}.log"
        run_0_versioned = logs_dir / f"agent-{agent_id}_run-0.log"
        if legacy_file.exists() and not run_0_versioned.exists():
            # Legacy file exists and no _run-0 file - read legacy file directly as run 0
            # Can't use _read_output_from_log(run_number=None) because that reads latest run
            chunks = self._read_log_file(legacy_file, backend_type=backend_type)
            if chunks:
                results.append((0, chunks))

        # Read each versioned log file
        for log_file in run_files:
            try:
                # Extract run number from filename
                # Format: agent-{id}_run-{run_number}.log
                filename = log_file.stem  # agent-{id}_run-{run_number}
                run_part = filename.split("_run-")[-1]
                run_number = int(run_part)
                chunks = self._read_output_from_log(agent_id, run_number=run_number, backend_type=backend_type)
                if chunks:
                    results.append((run_number, chunks))
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse log filename {log_file}: {e}")
                continue

        return sorted(results, key=lambda x: x[0])

    def iter_output(
        self,
        agent_id: str,
        timeout: float | None = None,
    ):
        """Iterate over new output chunks (blocking).

        Args:
            agent_id: The agent ID
            timeout: Timeout for each chunk (None = wait forever)

        Yields:
            OutputChunk objects as they arrive
        """
        managed = self.get_process(agent_id)
        if managed is None:
            return

        while True:
            try:
                chunk = managed.output_queue.get(timeout=timeout)
                yield chunk
            except queue.Empty:
                # Check if process is still running
                if managed.process.poll() is not None:
                    break
                continue

    def cleanup(self, agent_id: str) -> None:
        """Clean up a finished process."""
        with self._lock:
            managed = self._processes.pop(agent_id, None)

        if managed is None:
            return

        # Close PTY master fd if used
        if managed._pty_master_fd is not None:
            try:
                os.close(managed._pty_master_fd)
            except Exception:
                pass

        # Close log handle
        if managed._log_handle:
            try:
                managed._log_handle.close()
            except Exception:
                pass

        # Wait for threads to finish
        if managed.stdout_thread:
            managed.stdout_thread.join(timeout=1.0)
        if managed.stderr_thread:
            managed.stderr_thread.join(timeout=1.0)

    def cleanup_all(self) -> None:
        """Clean up all processes."""
        with self._lock:
            agent_ids = list(self._processes.keys())

        for agent_id in agent_ids:
            try:
                self.terminate(agent_id, timeout=2.0)
            except Exception:
                pass
            self.cleanup(agent_id)

    def list_running(self) -> list[str]:
        """Get list of running agent IDs."""
        with self._lock:
            return [
                agent_id
                for agent_id, managed in self._processes.items()
                if managed.process.poll() is None
            ]

    def poll_all(self) -> dict[str, int | None]:
        """Poll all processes and return their exit codes.

        Returns:
            Dict mapping agent_id to exit code (None if still running)
        """
        with self._lock:
            return {
                agent_id: managed.process.poll()
                for agent_id, managed in self._processes.items()
            }
