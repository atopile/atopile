"""Custom exceptions for the orchestrator framework."""

from __future__ import annotations


class OrchestratorError(Exception):
    """Base exception for all orchestrator errors."""


class AgentError(OrchestratorError):
    """Base exception for agent-related errors."""


class AgentNotFoundError(AgentError):
    """Raised when an agent is not found."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agent not found: {agent_id}")


class AgentAlreadyRunningError(AgentError):
    """Raised when trying to start an already running agent."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agent already running: {agent_id}")


class AgentNotRunningError(AgentError):
    """Raised when trying to interact with a non-running agent."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        super().__init__(f"Agent not running: {agent_id}")


class BackendError(OrchestratorError):
    """Base exception for backend-related errors."""


class BackendNotAvailableError(BackendError):
    """Raised when a backend is not available on this system."""

    def __init__(self, backend: str, reason: str | None = None) -> None:
        self.backend = backend
        self.reason = reason
        msg = f"Backend not available: {backend}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class BackendSpawnError(BackendError):
    """Raised when spawning an agent fails."""

    def __init__(self, backend: str, reason: str) -> None:
        self.backend = backend
        self.reason = reason
        super().__init__(f"Failed to spawn {backend} agent: {reason}")


class SessionError(OrchestratorError):
    """Base exception for session-related errors."""


class SessionNotFoundError(SessionError):
    """Raised when a session is not found."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class ProcessError(OrchestratorError):
    """Base exception for process-related errors."""


class ProcessNotRunningError(ProcessError):
    """Raised when trying to interact with a non-running process."""

    def __init__(self, process_id: str) -> None:
        self.process_id = process_id
        super().__init__(f"Process not running: {process_id}")
