"""
Dependency injection for the server.

This module provides singleton instances and dependency injection
for FastAPI routes, enabling proper testability.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import Depends

log = logging.getLogger(__name__)


class ServerConfig:
    """Server configuration."""

    def __init__(
        self,
        logs_base: Optional[Path] = None,
        workspace_paths: Optional[list[Path]] = None,
        port: int = 8501,
        host: str = "127.0.0.1",
    ):
        self.logs_base = logs_base
        self.workspace_paths = workspace_paths or []
        self.port = port
        self.host = host


class AppDependencies:
    """
    Singleton holding shared application dependencies.

    This allows dependency injection for routes and makes testing easier.
    """

    _instance: Optional["AppDependencies"] = None

    def __init__(self, config: Optional[ServerConfig] = None):
        self.config = config or ServerConfig()
        self._build_queue = None
        self._server_state = None

    @classmethod
    def get_instance(cls) -> "AppDependencies":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton (for testing)."""
        cls._instance = None

    @property
    def build_queue(self):
        """Get the build queue (lazy-loaded from server.py)."""
        if self._build_queue is None:
            from .server import build_queue
            self._build_queue = build_queue
        return self._build_queue

    @property
    def server_state(self):
        """Get the server state singleton."""
        if self._server_state is None:
            from .state import server_state
            self._server_state = server_state
        return self._server_state

    @property
    def logs_base(self) -> Optional[Path]:
        """Get the logs base directory."""
        # First check config, then server state
        if self.config.logs_base:
            return self.config.logs_base

        from .server import state
        return state.get("logs_base")

    @property
    def workspace_paths(self) -> list[Path]:
        """Get workspace paths."""
        if self.config.workspace_paths:
            return self.config.workspace_paths

        from .server import state
        return state.get("workspace_paths", [])


# Dependency functions for FastAPI


def get_deps() -> AppDependencies:
    """FastAPI dependency to get AppDependencies."""
    return AppDependencies.get_instance()


def get_config(deps: AppDependencies = Depends(get_deps)) -> ServerConfig:
    """FastAPI dependency to get ServerConfig."""
    return deps.config


def get_build_queue(deps: AppDependencies = Depends(get_deps)):
    """FastAPI dependency to get the build queue."""
    return deps.build_queue


def get_server_state(deps: AppDependencies = Depends(get_deps)):
    """FastAPI dependency to get the server state."""
    return deps.server_state


def get_logs_base(deps: AppDependencies = Depends(get_deps)) -> Optional[Path]:
    """FastAPI dependency to get logs base directory."""
    return deps.logs_base


def get_workspace_paths(deps: AppDependencies = Depends(get_deps)) -> list[Path]:
    """FastAPI dependency to get workspace paths."""
    return deps.workspace_paths
