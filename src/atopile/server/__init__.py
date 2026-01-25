"""
Atopile Server - FastAPI backend for the atopile VS Code extension.

This package provides:
- REST API endpoints for projects, builds, packages
- WebSocket connections for real-time events
- Build queue management
- Package registry integration

Directory Structure:
- server.py: Main FastAPI app and route handlers (being refactored)
- connections.py: ServerConnections singleton for event delivery
- stdlib.py: Standard library introspection
- routes/: FastAPI routers by domain (projects, builds, packages, etc.)

Note: All data classes and Pydantic models are defined in atopile.dataclasses
"""

from .server import create_app, DashboardServer, start_dashboard_server

__all__ = [
    "create_app",
    "DashboardServer",
    "start_dashboard_server",
]
