"""Agent runtime: LLM-driven tool execution for atopile projects."""

from atopile.server.agent.config import AgentConfig
from atopile.server.agent.provider import LLMProvider, OpenAIProvider
from atopile.server.agent.registry import ToolRegistry
from atopile.server.agent.runner import AgentRunner, AgentTurnResult, ToolTrace

# Backward-compat alias — routes and other code still reference this name.
AgentOrchestrator = AgentRunner

__all__ = [
    "AgentConfig",
    "AgentOrchestrator",
    "AgentRunner",
    "AgentTurnResult",
    "LLMProvider",
    "OpenAIProvider",
    "ToolTrace",
    "ToolRegistry",
]
