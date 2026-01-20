"""API routes for the orchestrator server."""

from .agents import router as agents_router
from .bridge import router as bridge_router
from .pipelines import router as pipelines_router
from .sessions import router as sessions_router
from .websocket import router as websocket_router

__all__ = [
    "agents_router",
    "bridge_router",
    "pipelines_router",
    "sessions_router",
    "websocket_router",
]
