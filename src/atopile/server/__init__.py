"""
atopile Server - FastAPI backend for atopile.

This package provides:
- REST API endpoints for projects, builds, packages
- Build queue management
- Package registry integration

Directory Structure:
- server.py: Main FastAPI app and route handlers
- stdlib.py: Standard library introspection
- routes/: FastAPI routers by domain (projects, builds, packages, etc.)

Note: All data classes and Pydantic models are defined in atopile.dataclasses
"""

from .server import DashboardServer, create_app, start_dashboard_server

__all__ = [
    "create_app",
    "DashboardServer",
    "start_dashboard_server",
]
