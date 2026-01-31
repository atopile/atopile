"""
API Routes for the dashboard server.

This module contains all FastAPI routers organized by domain:
- projects: Project discovery and management
- builds: Build execution and status
- packages: Package management and registry
- parts-search: Part search/install
- problems: Build problem reporting
- artifacts: BOM, variables, stdlib, and resolve-location
- parts: LCSC part data
- websocket: Real-time state updates
- logs: Build log querying
- tests: Test discovery and execution
"""

from .artifacts import router as artifacts_router
from .builds import router as builds_router
from .logs import router as logs_router
from .packages import router as packages_router
from .parts import router as parts_router
from .parts_search import router as parts_search_router
from .problems import router as problems_router
from .projects import router as projects_router
from .tests import router as tests_router
from .websocket import router as websocket_router

__all__ = [
    "artifacts_router",
    "builds_router",
    "parts_search_router",
    "logs_router",
    "parts_router",
    "packages_router",
    "problems_router",
    "projects_router",
    "tests_router",
    "websocket_router",
]
