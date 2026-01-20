"""Base agent backend interface."""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from ..models import AgentBackendType, AgentCapabilities, AgentConfig, OutputChunk

if TYPE_CHECKING:
    pass


class AgentBackend(ABC):
    """Abstract base class for agent backends.

    Each backend (claude-code, codex, cursor, etc.) implements this interface
    to provide a unified way to spawn and interact with agents.
    """

    @property
    @abstractmethod
    def backend_type(self) -> AgentBackendType:
        """Return the backend type identifier."""
        ...

    @property
    @abstractmethod
    def binary_name(self) -> str:
        """Return the name of the CLI binary."""
        ...

    @abstractmethod
    def get_capabilities(self) -> AgentCapabilities:
        """Return the capabilities of this backend."""
        ...

    def is_available(self) -> bool:
        """Check if this backend is available on the system."""
        return self.get_binary_path() is not None

    def get_binary_path(self) -> Path | None:
        """Get the path to the backend binary, or None if not found."""
        path = shutil.which(self.binary_name)
        return Path(path) if path else None

    @abstractmethod
    def build_command(self, config: AgentConfig) -> list[str]:
        """Build the command line arguments to spawn an agent.

        Args:
            config: The agent configuration

        Returns:
            List of command line arguments (including the binary path)
        """
        ...

    @abstractmethod
    def parse_output_line(self, line: str, sequence: int) -> OutputChunk | None:
        """Parse a line of output from the agent.

        Args:
            line: Raw line of output from stdout/stderr
            sequence: Sequence number for ordering

        Returns:
            Parsed OutputChunk, or None if the line should be ignored
        """
        ...

    @abstractmethod
    def extract_session_id(self, chunk: OutputChunk) -> str | None:
        """Extract a session ID from an output chunk if present.

        Args:
            chunk: Output chunk to examine

        Returns:
            Session ID if found, None otherwise
        """
        ...

    def get_resume_args(self, session_id: str) -> list[str]:
        """Get additional arguments for resuming a session.

        Args:
            session_id: The session ID to resume

        Returns:
            List of additional command line arguments
        """
        return []


def get_backend(backend_type: AgentBackendType) -> AgentBackend:
    """Get a backend instance by type.

    Args:
        backend_type: The type of backend to get

    Returns:
        An instance of the appropriate backend

    Raises:
        ValueError: If the backend type is not supported
    """
    from .claude import ClaudeCodeBackend
    from .codex import CodexBackend

    backends: dict[AgentBackendType, type[AgentBackend]] = {
        AgentBackendType.CLAUDE_CODE: ClaudeCodeBackend,
        AgentBackendType.CODEX: CodexBackend,
    }

    backend_class = backends.get(backend_type)
    if backend_class is None:
        raise ValueError(f"Unsupported backend type: {backend_type}")

    return backend_class()


def get_available_backends() -> list[AgentBackend]:
    """Get all available backends on this system."""
    from .claude import ClaudeCodeBackend
    from .codex import CodexBackend

    all_backends: list[AgentBackend] = [
        ClaudeCodeBackend(),
        CodexBackend(),
    ]

    return [b for b in all_backends if b.is_available()]
