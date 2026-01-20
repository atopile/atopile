"""Agent Orchestration Framework.

A unified interface for spawning and managing AI coding agents
(claude-code, codex, cursor-cli) with REST API and WebSocket streaming.

Example usage:

    # As a library
    from tools.orchestrator import ProcessManager, AgentConfig, AgentState

    pm = ProcessManager()
    config = AgentConfig(backend="claude-code", prompt="Hello")
    agent = AgentState(config=config)
    pm.spawn(agent)

    # As a CLI
    python -m tools.orchestrator serve --port 8765

    # Or via the CLI module
    python -m tools.orchestrator.cli.main spawn "What is 2+2?"
"""

from .agents import AgentBackend, ClaudeCodeBackend, get_available_backends, get_backend
from .common import DEFAULT_HOST, DEFAULT_PORT
from .core import (
    AgentStateStore,
    ManagedProcess,
    ProcessManager,
    SessionManager,
    SessionStateStore,
    StateStore,
)
from .exceptions import (
    AgentError,
    AgentNotFoundError,
    AgentNotRunningError,
    BackendError,
    BackendNotAvailableError,
    BackendSpawnError,
    OrchestratorError,
    ProcessError,
    SessionError,
    SessionNotFoundError,
)
from .models import (
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
    StreamEvent,
    StreamEventType,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Constants
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    # Agent backends
    "AgentBackend",
    "ClaudeCodeBackend",
    "get_available_backends",
    "get_backend",
    # Core components
    "AgentStateStore",
    "ManagedProcess",
    "ProcessManager",
    "SessionManager",
    "SessionStateStore",
    "StateStore",
    # Exceptions
    "AgentError",
    "AgentNotFoundError",
    "AgentNotRunningError",
    "BackendError",
    "BackendNotAvailableError",
    "BackendSpawnError",
    "OrchestratorError",
    "ProcessError",
    "SessionError",
    "SessionNotFoundError",
    # Models
    "AgentBackendType",
    "AgentCapabilities",
    "AgentConfig",
    "AgentState",
    "AgentStatus",
    "ClaudeCodeMessage",
    "OutputChunk",
    "OutputType",
    "SessionMetadata",
    "SessionState",
    "SessionStatus",
    "StreamEvent",
    "StreamEventType",
]
