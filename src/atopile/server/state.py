"""
AppState management for the dashboard server.

This module provides a centralized state management system where:
- Python owns ALL state (single source of truth)
- State is pushed to clients via WebSocket on every change
- Actions from clients modify state and trigger broadcasts

Architecture:
- AppState: Pydantic model mirroring the frontend TypeScript types
- ServerState: Singleton holding mutable state, methods to update it
- WebSocket pushes full state on connect and on any mutation
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional

from fastapi import WebSocket

from atopile.dataclasses import (
    AppState,
    BOMData,
    Build,
    ConnectedClient,
    DependencyInfo,
    DetectedInstallation,
    FileTreeNode,
    ModuleDefinition,
    PackageDetails,
    PackageInfo,
    Problem,
    Project,
    StdLibItem,
    VariablesData,
)

log = logging.getLogger(__name__)


class ServerState:
    """
    Singleton managing all server state.

    - Holds the current AppState
    - Provides methods to update state
    - Broadcasts full state to all clients on any change
    """

    _instance: Optional["ServerState"] = None

    def __new__(cls) -> "ServerState":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._state = AppState()
        self._clients: dict[str, ConnectedClient] = {}
        self._lock = asyncio.Lock()
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._workspace_paths: list[Path] = []

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Store the event loop for background thread broadcasts."""
        self._event_loop = loop
        log.info("ServerState: Event loop captured")

    def set_workspace_paths(self, paths: list[Path]) -> None:
        """Set workspace paths for project discovery."""
        self._workspace_paths = paths

    @property
    def state(self) -> AppState:
        """Get current state (read-only access)."""
        return self._state

    @property
    def packages_by_id(self) -> dict[str, PackageInfo]:
        """Get packages indexed by identifier for quick lookup."""
        return {pkg.identifier: pkg for pkg in self._state.packages}

    async def connect_client(self, websocket: WebSocket) -> str:
        """Accept a WebSocket connection and return client ID."""
        await websocket.accept()
        client_id = str(uuid.uuid4())[:8]

        async with self._lock:
            self._clients[client_id] = ConnectedClient(
                client_id=client_id, websocket=websocket
            )

        log.info(f"Client {client_id} connected (total: {len(self._clients)})")

        # Send current state immediately
        await self._send_state_to_client(client_id)

        return client_id

    async def disconnect_client(self, client_id: str) -> None:
        """Remove a disconnected client."""
        async with self._lock:
            self._clients.pop(client_id, None)
        log.info(f"Client {client_id} disconnected (total: {len(self._clients)})")

    async def _send_state_to_client(self, client_id: str) -> bool:
        """Send current state to a specific client."""
        client = self._clients.get(client_id)
        if not client or not client.subscribed:
            return False

        try:
            message = {
                "type": "state",
                "data": self._state.to_frontend_dict(),
            }
            await client.websocket.send_json(message)
            return True
        except Exception as e:
            log.warning(f"Failed to send state to client {client_id}: {e}")
            return False

    async def broadcast_state(self) -> None:
        """Broadcast current state to all connected clients."""
        if not self._clients:
            return

        message = {
            "type": "state",
            "data": self._state.to_frontend_dict(),
        }

        dead_clients: list[str] = []

        async with self._lock:
            for client_id, client in self._clients.items():
                if not client.subscribed:
                    continue
                try:
                    await client.websocket.send_json(message)
                except Exception:
                    dead_clients.append(client_id)

            # Clean up dead clients
            for client_id in dead_clients:
                self._clients.pop(client_id, None)

        if dead_clients:
            log.info(f"Removed {len(dead_clients)} dead clients")

    def broadcast_state_sync(self) -> None:
        """Broadcast state from synchronous code."""
        if self._event_loop and self._event_loop.is_running():
            asyncio.run_coroutine_threadsafe(self.broadcast_state(), self._event_loop)
        else:
            log.warning("No event loop available for state broadcast")

    # --- State Mutation Methods ---
    # Each method modifies state and triggers a broadcast

    async def set_projects(
        self, projects: list[Project], error: Optional[str] = None
    ) -> None:
        """Update projects list."""
        self._state.projects = projects
        self._state.projects_error = error
        self._state.is_loading_projects = False
        await self.broadcast_state()

    async def set_loading_projects(self, loading: bool) -> None:
        """Set projects loading state."""
        self._state.is_loading_projects = loading
        await self.broadcast_state()

    async def set_selected_project(self, project_root: Optional[str]) -> None:
        """Set the selected project."""
        self._state.selected_project_root = project_root
        await self.broadcast_state()

    async def set_selected_targets(self, target_names: list[str]) -> None:
        """Set selected target names."""
        self._state.selected_target_names = target_names
        await self.broadcast_state()

    async def toggle_target(self, target_name: str) -> None:
        """Toggle a target selection."""
        if target_name in self._state.selected_target_names:
            self._state.selected_target_names.remove(target_name)
        else:
            self._state.selected_target_names.append(target_name)
        await self.broadcast_state()

    async def set_builds(self, builds: list[Build]) -> None:
        """Update builds list."""
        self._state.builds = builds
        await self.broadcast_state()

    async def set_queued_builds(self, queued: list[Build]) -> None:
        """Update queued builds."""
        self._state.queued_builds = queued
        await self.broadcast_state()

    async def set_packages(
        self, packages: list[PackageInfo], error: Optional[str] = None
    ) -> None:
        """Update packages list."""
        self._state.packages = packages
        self._state.packages_error = error
        self._state.is_loading_packages = False
        await self.broadcast_state()

    async def set_loading_packages(self, loading: bool) -> None:
        """Set packages loading state."""
        self._state.is_loading_packages = loading
        await self.broadcast_state()

    async def set_selected_build(self, build_name: Optional[str]) -> None:
        """Set the selected build."""
        self._state.selected_build_name = build_name
        await self.broadcast_state()

    async def set_atopile_source(self, source: str) -> None:
        """Set atopile source (release/branch/local)."""
        self._state.atopile.source = source
        await self.broadcast_state()

    async def set_atopile_version(self, version: str) -> None:
        """Set current atopile version string."""
        self._state.atopile.current_version = version
        await self.broadcast_state()

    async def set_atopile_branch(self, branch: Optional[str]) -> None:
        """Set current atopile branch."""
        self._state.atopile.branch = branch
        await self.broadcast_state()

    async def set_atopile_local_path(self, path: Optional[str]) -> None:
        """Set local atopile path."""
        self._state.atopile.local_path = path
        await self.broadcast_state()

    async def set_atopile_available_versions(self, versions: list[str]) -> None:
        """Set available atopile versions from PyPI."""
        self._state.atopile.available_versions = versions
        await self.broadcast_state()

    async def set_atopile_available_branches(self, branches: list[str]) -> None:
        """Set available atopile branches from GitHub."""
        self._state.atopile.available_branches = branches
        await self.broadcast_state()

    async def set_atopile_detected_installations(
        self, installations: list[dict]
    ) -> None:
        """Set detected local atopile installations."""
        self._state.atopile.detected_installations = [
            DetectedInstallation(**inst) for inst in installations
        ]
        await self.broadcast_state()

    async def toggle_target_expanded(self, target_name: str) -> None:
        """Toggle target expansion in sidebar."""
        if target_name in self._state.expanded_targets:
            self._state.expanded_targets.remove(target_name)
        else:
            self._state.expanded_targets.append(target_name)
        await self.broadcast_state()

    async def set_problems(self, problems: list[Problem]) -> None:
        """Update problems list."""
        self._state.problems = problems
        self._state.is_loading_problems = False
        await self.broadcast_state()

    async def toggle_problem_level_filter(self, level: str) -> None:
        """Toggle a problem level filter (error/warning)."""
        levels = list(self._state.problem_filter.levels)
        if level in levels:
            if len(levels) > 1:
                levels.remove(level)
        else:
            levels.append(level)

        self._state.problem_filter.levels = levels
        await self.broadcast_state()

    async def set_developer_mode(self, enabled: bool) -> None:
        """Set developer mode and refresh problems with appropriate audience filter."""
        self._state.developer_mode = enabled
        # Refresh problems with new audience filter
        from atopile.server.problem_parser import sync_problems_to_state_async

        await sync_problems_to_state_async(developer_mode=enabled)
        # broadcast_state is called by sync_problems_to_state_async via set_problems

    async def set_stdlib_items(self, items: list[StdLibItem]) -> None:
        """Update stdlib items."""
        self._state.stdlib_items = items
        self._state.is_loading_stdlib = False
        await self.broadcast_state()

    async def set_bom_data(
        self, bom: Optional[BOMData], error: Optional[str] = None
    ) -> None:
        """Update BOM data."""
        self._state.bom_data = bom
        self._state.bom_error = error
        self._state.is_loading_bom = False
        await self.broadcast_state()

    async def set_package_details(
        self, details: Optional[PackageDetails], error: Optional[str] = None
    ) -> None:
        """Update selected package details."""
        self._state.selected_package_details = details
        self._state.package_details_error = error
        self._state.is_loading_package_details = False
        await self.broadcast_state()

    async def set_project_modules(
        self, project_root: str, modules: list[ModuleDefinition]
    ) -> None:
        """Update modules for a project."""
        self._state.project_modules[project_root] = modules
        self._state.is_loading_modules = False
        await self.broadcast_state()

    async def set_project_files(
        self, project_root: str, files: list[FileTreeNode]
    ) -> None:
        """Update files for a project."""
        self._state.project_files[project_root] = files
        self._state.is_loading_files = False
        await self.broadcast_state()

    async def set_project_dependencies(
        self, project_root: str, dependencies: list[DependencyInfo]
    ) -> None:
        """Update dependencies for a project."""
        self._state.project_dependencies[project_root] = dependencies
        self._state.is_loading_dependencies = False
        await self.broadcast_state()

    async def set_variables_data(
        self, data: Optional[VariablesData], error: Optional[str] = None
    ) -> None:
        """Update variables data."""
        self._state.current_variables_data = data
        self._state.variables_error = error
        self._state.is_loading_variables = False
        await self.broadcast_state()


# Global singleton instance
server_state = ServerState()
