"""
AppState management for the dashboard server.

This module provides a centralized state management system where:
- Python owns ALL state (single source of truth)
- State is pushed to clients via WebSocket on every change
- Actions from clients modify state and trigger broadcasts

Architecture:
- AppState: Pydantic model mirroring the frontend TypeScript types
- ServerState: Class holding mutable state, methods to update it
- WebSocket pushes full state on connect and on any mutation

Usage:
- For route handlers: use `get_server_state()` dependency
- For background tasks: import `server_state` from this module
- For testing: use `reset_server_state()` between tests
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
    Central state manager for the dashboard server.

    - Holds the current AppState
    - Provides methods to update state
    - Broadcasts full state to all clients on any change

    Note: This is NOT a singleton. A module-level instance `server_state` is
    created for convenience, but you can create additional instances for testing.
    """

    def __init__(self):
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
        """
        Broadcast current state to all connected clients.

        This method acquires the lock to ensure thread-safe access to clients.
        For internal use where the lock is already held, use _broadcast_state_unlocked.
        """
        async with self._lock:
            await self._broadcast_state_unlocked()

    async def _broadcast_state_unlocked(self) -> None:
        """
        Internal broadcast method - caller must hold self._lock.

        Serializes state and sends to all subscribed clients.
        Removes any clients that fail to receive the message.
        """
        if not self._clients:
            return

        message = {
            "type": "state",
            "data": self._state.to_frontend_dict(),
        }

        dead_clients: list[str] = []

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
    # Each method modifies state and triggers a broadcast.
    # All mutations are protected by self._lock to ensure atomicity
    # of state changes and their broadcast to clients.

    async def set_projects(
        self, projects: list[Project], error: Optional[str] = None
    ) -> None:
        """Update projects list."""
        async with self._lock:
            self._state.projects = projects
            self._state.projects_error = error
            self._state.is_loading_projects = False
            await self._broadcast_state_unlocked()

    async def set_loading_projects(self, loading: bool) -> None:
        """Set projects loading state."""
        async with self._lock:
            self._state.is_loading_projects = loading
            await self._broadcast_state_unlocked()

    async def set_selected_project(self, project_root: Optional[str]) -> None:
        """Set the selected project."""
        async with self._lock:
            self._state.selected_project_root = project_root
            await self._broadcast_state_unlocked()

    async def set_selected_targets(self, target_names: list[str]) -> None:
        """Set selected target names."""
        async with self._lock:
            self._state.selected_target_names = target_names
            await self._broadcast_state_unlocked()

    async def toggle_target(self, target_name: str) -> None:
        """Toggle a target selection."""
        async with self._lock:
            if target_name in self._state.selected_target_names:
                self._state.selected_target_names.remove(target_name)
            else:
                self._state.selected_target_names.append(target_name)
            await self._broadcast_state_unlocked()

    async def set_builds(self, builds: list[Build]) -> None:
        """Update builds list."""
        async with self._lock:
            self._state.builds = builds
            await self._broadcast_state_unlocked()

    async def set_queued_builds(self, queued: list[Build]) -> None:
        """Update queued builds."""
        async with self._lock:
            self._state.queued_builds = queued
            await self._broadcast_state_unlocked()

    async def set_packages(
        self, packages: list[PackageInfo], error: Optional[str] = None
    ) -> None:
        """Update packages list."""
        async with self._lock:
            self._state.packages = packages
            self._state.packages_error = error
            self._state.is_loading_packages = False
            await self._broadcast_state_unlocked()

    async def set_loading_packages(self, loading: bool) -> None:
        """Set packages loading state."""
        async with self._lock:
            self._state.is_loading_packages = loading
            await self._broadcast_state_unlocked()

    async def add_installing_package(self, package_id: str) -> None:
        """Track a package install in progress."""
        async with self._lock:
            if package_id not in self._state.installing_package_ids:
                self._state.installing_package_ids.append(package_id)
            self._state.install_error = None
            await self._broadcast_state_unlocked()

    async def remove_installing_package(
        self, package_id: str, error: Optional[str] = None
    ) -> None:
        """Stop tracking a package install."""
        async with self._lock:
            if package_id in self._state.installing_package_ids:
                self._state.installing_package_ids.remove(package_id)
            if error:
                self._state.install_error = error
            await self._broadcast_state_unlocked()

    async def set_selected_build(self, build_name: Optional[str]) -> None:
        """Set the selected build."""
        async with self._lock:
            self._state.selected_build_name = build_name
            await self._broadcast_state_unlocked()

    async def set_atopile_source(self, source: str) -> None:
        """Set atopile source (release/branch/local)."""
        async with self._lock:
            self._state.atopile.source = source
            await self._broadcast_state_unlocked()

    async def set_atopile_version(self, version: str) -> None:
        """Set current atopile version string."""
        async with self._lock:
            self._state.atopile.current_version = version
            await self._broadcast_state_unlocked()

    async def set_atopile_branch(self, branch: Optional[str]) -> None:
        """Set current atopile branch."""
        async with self._lock:
            self._state.atopile.branch = branch
            await self._broadcast_state_unlocked()

    async def set_atopile_local_path(self, path: Optional[str]) -> None:
        """Set local atopile path."""
        async with self._lock:
            self._state.atopile.local_path = path
            await self._broadcast_state_unlocked()

    async def set_atopile_available_versions(self, versions: list[str]) -> None:
        """Set available atopile versions from PyPI."""
        async with self._lock:
            self._state.atopile.available_versions = versions
            await self._broadcast_state_unlocked()

    async def set_atopile_available_branches(self, branches: list[str]) -> None:
        """Set available atopile branches from GitHub."""
        async with self._lock:
            self._state.atopile.available_branches = branches
            await self._broadcast_state_unlocked()

    async def set_atopile_installing(
        self, installing: bool, error: Optional[str] = None
    ) -> None:
        """Set atopile install status and optional error."""
        async with self._lock:
            self._state.atopile.is_installing = installing
            self._state.atopile.error = error
            if not installing:
                self._state.atopile.install_progress = None
            await self._broadcast_state_unlocked()

    async def set_atopile_detected_installations(
        self, installations: list[dict]
    ) -> None:
        """Set detected local atopile installations."""
        async with self._lock:
            self._state.atopile.detected_installations = [
                DetectedInstallation(**inst) for inst in installations
            ]
            await self._broadcast_state_unlocked()

    async def toggle_target_expanded(self, target_name: str) -> None:
        """Toggle target expansion in sidebar."""
        async with self._lock:
            if target_name in self._state.expanded_targets:
                self._state.expanded_targets.remove(target_name)
            else:
                self._state.expanded_targets.append(target_name)
            await self._broadcast_state_unlocked()

    async def set_problems(self, problems: list[Problem]) -> None:
        """Update problems list."""
        async with self._lock:
            self._state.problems = problems
            self._state.is_loading_problems = False
            await self._broadcast_state_unlocked()

    async def toggle_problem_level_filter(self, level: str) -> None:
        """Toggle a problem level filter (error/warning)."""
        async with self._lock:
            levels = list(self._state.problem_filter.levels)
            if level in levels:
                if len(levels) > 1:
                    levels.remove(level)
            else:
                levels.append(level)

            self._state.problem_filter.levels = levels
            await self._broadcast_state_unlocked()

    async def set_developer_mode(self, enabled: bool) -> None:
        """Set developer mode and refresh problems with appropriate audience filter."""
        async with self._lock:
            self._state.developer_mode = enabled
            await self._broadcast_state_unlocked()

        # Refresh problems with new audience filter (outside lock to avoid deadlock)
        from atopile.server.problem_parser import sync_problems_to_state_async

        await sync_problems_to_state_async(developer_mode=enabled)

    async def set_stdlib_items(self, items: list[StdLibItem]) -> None:
        """Update stdlib items."""
        async with self._lock:
            self._state.stdlib_items = items
            self._state.is_loading_stdlib = False
            await self._broadcast_state_unlocked()

    async def set_bom_data(
        self, bom: Optional[BOMData | dict], error: Optional[str] = None
    ) -> None:
        """Update BOM data."""
        if isinstance(bom, dict):
            try:
                bom = BOMData.model_validate(bom)
            except Exception as exc:
                log.warning("Failed to parse BOMData payload: %s", exc)
                bom = None
                error = error or "Invalid BOM data"
        async with self._lock:
            self._state.bom_data = bom
            self._state.bom_error = error
            self._state.is_loading_bom = False
            await self._broadcast_state_unlocked()

    async def set_package_details(
        self, details: Optional[PackageDetails], error: Optional[str] = None
    ) -> None:
        """Update selected package details."""
        async with self._lock:
            self._state.selected_package_details = details
            self._state.package_details_error = error
            self._state.is_loading_package_details = False
            await self._broadcast_state_unlocked()

    async def set_project_modules(
        self, project_root: str, modules: list[ModuleDefinition]
    ) -> None:
        """Update modules for a project."""
        async with self._lock:
            self._state.project_modules[project_root] = modules
            self._state.is_loading_modules = False
            await self._broadcast_state_unlocked()

    async def set_project_files(
        self, project_root: str, files: list[FileTreeNode]
    ) -> None:
        """Update files for a project."""
        async with self._lock:
            self._state.project_files[project_root] = files
            self._state.is_loading_files = False
            await self._broadcast_state_unlocked()

    async def set_project_dependencies(
        self, project_root: str, dependencies: list[DependencyInfo]
    ) -> None:
        """Update dependencies for a project."""
        async with self._lock:
            self._state.project_dependencies[project_root] = dependencies
            self._state.is_loading_dependencies = False
            await self._broadcast_state_unlocked()

    async def set_variables_data(
        self, data: Optional[VariablesData | dict], error: Optional[str] = None
    ) -> None:
        """Update variables data."""
        if isinstance(data, dict):
            try:
                data = VariablesData.model_validate(data)
            except Exception as exc:
                log.warning("Failed to parse VariablesData payload: %s", exc)
                data = None
                error = error or "Invalid variables data"
        async with self._lock:
            self._state.current_variables_data = data
            self._state.variables_error = error
            self._state.is_loading_variables = False
            await self._broadcast_state_unlocked()

    async def set_open_file(
        self,
        file_path: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ) -> None:
        """Signal to open a file in the editor."""
        async with self._lock:
            self._state.open_file = file_path
            self._state.open_file_line = line
            self._state.open_file_column = column
            await self._broadcast_state_unlocked()
            # Clear after broadcast so it acts as a one-shot signal
            self._state.open_file = None
            self._state.open_file_line = None
            self._state.open_file_column = None

    async def set_open_layout(self, layout_path: str) -> None:
        """Signal to open a layout file."""
        async with self._lock:
            self._state.open_layout = layout_path
            await self._broadcast_state_unlocked()
            # Clear after broadcast so it acts as a one-shot signal
            self._state.open_layout = None

    async def set_open_kicad(self, kicad_path: str) -> None:
        """Signal to open KiCad with a project."""
        async with self._lock:
            self._state.open_kicad = kicad_path
            await self._broadcast_state_unlocked()
            # Clear after broadcast so it acts as a one-shot signal
            self._state.open_kicad = None

    async def set_open_3d(self, model_path: str) -> None:
        """Signal to open the 3D viewer."""
        async with self._lock:
            self._state.open_3d = model_path
            await self._broadcast_state_unlocked()
            # Clear after broadcast so it acts as a one-shot signal
            self._state.open_3d = None


# Module-level instance for the application
# - For route handlers: use get_server_state() dependency
# - For background tasks: import this directly
# - For testing: use reset_server_state() to get a fresh instance
server_state = ServerState()


def get_server_state() -> ServerState:
    """
    FastAPI dependency to get the server state.

    Usage in route handlers:
        @router.get("/api/state")
        async def get_state(state: ServerState = Depends(get_server_state)):
            return state.get_state()

    For background tasks, import `server_state` directly instead.
    """
    return server_state


def reset_server_state() -> ServerState:
    """
    Reset the server state to a fresh instance.

    Intended for use in tests to ensure clean state between test cases.
    Returns the new instance.

    Usage:
        def test_something():
            state = reset_server_state()
            # ... test with clean state
    """
    global server_state
    server_state = ServerState()
    return server_state
