"""
API Routes for the dashboard server.

This module contains all FastAPI routers organized by domain:
- projects: Project discovery and management
- builds: Build execution and status
- packages: Package management and registry
- problems: Build problem reporting
- artifacts: BOM, variables, stdlib, and resolve-location
- websocket: Real-time state updates
"""

from .artifacts import router as artifacts_router
from .builds import router as builds_router
from .packages import router as packages_router
from .problems import router as problems_router
from .projects import router as projects_router
from .websocket import router as websocket_router

__all__ = [
    "artifacts_router",
    "builds_router",
    "packages_router",
    "problems_router",
    "projects_router",
    "websocket_router",
]
