"""
API Routes for the dashboard server.

This module contains all FastAPI routers organized by domain:
- projects: Project discovery and management
- builds: Build execution and status
- packages: Package management and registry
- logs: Log querying and streaming
- problems: Build problem reporting
- artifacts: BOM, variables, and other build artifacts
- websocket: Real-time state updates
"""

from .projects import router as projects_router
from .builds import router as builds_router
from .packages import router as packages_router
from .logs import router as logs_router
from .problems import router as problems_router
from .artifacts import router as artifacts_router
from .websocket import router as websocket_router

__all__ = [
    "projects_router",
    "builds_router",
    "packages_router",
    "logs_router",
    "problems_router",
    "artifacts_router",
    "websocket_router",
]
