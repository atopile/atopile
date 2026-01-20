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
import json
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import WebSocket
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


# --- Log Entry Types ---


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "ALERT"]


class LogEntry(BaseModel):
    """A single log entry."""

    timestamp: str
    level: LogLevel
    logger: str = ""
    stage: str = ""
    message: str
    ato_traceback: Optional[str] = None
    exc_info: Optional[str] = None


# --- Build Types ---


BuildStatus = Literal["queued", "building", "success", "warning", "failed", "cancelled"]
StageStatus = Literal[
    "pending", "running", "success", "warning", "failed", "error", "skipped"
]


class BuildStage(BaseModel):
    """A stage within a build."""

    name: str
    stage_id: str
    display_name: Optional[str] = None
    elapsed_seconds: float = 0.0
    status: StageStatus = "pending"
    infos: int = 0
    warnings: int = 0
    errors: int = 0
    alerts: int = 0


class BuildTargetStatus(BaseModel):
    """Persisted status from last build of a target."""

    status: BuildStatus
    timestamp: str  # ISO format
    elapsed_seconds: Optional[float] = None
    warnings: int = 0
    errors: int = 0
    stages: Optional[list[dict]] = None


class BuildTarget(BaseModel):
    """A build target from ato.yaml."""

    name: str
    entry: str
    root: str
    last_build: Optional[BuildTargetStatus] = None


class Project(BaseModel):
    """A project discovered from ato.yaml."""

    root: str
    name: str
    targets: list[BuildTarget]


class Build(BaseModel):
    """A build (active, queued, or completed)."""

    # Core identification
    name: str
    display_name: str
    project_name: Optional[str] = None
    build_id: Optional[str] = None

    # Status
    status: BuildStatus = "queued"
    elapsed_seconds: float = 0.0
    warnings: int = 0
    errors: int = 0
    return_code: Optional[int] = None
    error: Optional[str] = None  # Error message from build failure

    # Context
    project_root: Optional[str] = None
    targets: Optional[list[str]] = None
    entry: Optional[str] = None
    started_at: Optional[float] = None

    # Stages and logs
    stages: Optional[list[BuildStage]] = None
    log_dir: Optional[str] = None
    log_file: Optional[str] = None

    # Queue info
    queue_position: Optional[int] = None


# --- Package Types ---


class PackageInfo(BaseModel):
    """Package information for display."""

    identifier: str
    name: str
    publisher: str
    version: Optional[str] = None
    latest_version: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    installed: bool = False
    installed_in: list[str] = Field(default_factory=list)
    has_update: bool = False
    downloads: Optional[int] = None
    version_count: Optional[int] = None
    keywords: Optional[list[str]] = None


class PackageVersion(BaseModel):
    """Package version information."""

    version: str
    released_at: Optional[str] = None
    requires_atopile: Optional[str] = None
    size: Optional[int] = None


class PackageDetails(BaseModel):
    """Detailed package information from registry."""

    identifier: str
    name: str
    publisher: str
    version: str
    summary: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    downloads: Optional[int] = None
    downloads_this_week: Optional[int] = None
    downloads_this_month: Optional[int] = None
    versions: list[PackageVersion] = Field(default_factory=list)
    version_count: int = 0
    installed: bool = False
    installed_version: Optional[str] = None
    installed_in: list[str] = Field(default_factory=list)


# --- Problem Types ---


class Problem(BaseModel):
    """A problem (error or warning) from a build."""

    id: str
    level: Literal["error", "warning"]
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    stage: Optional[str] = None
    logger: Optional[str] = None
    build_name: Optional[str] = None
    project_name: Optional[str] = None
    timestamp: Optional[str] = None
    ato_traceback: Optional[str] = None
    exc_info: Optional[str] = None


class ProblemFilter(BaseModel):
    """Filter settings for problems."""

    levels: list[Literal["error", "warning"]] = Field(
        default_factory=lambda: ["error", "warning"]
    )
    build_names: list[str] = Field(default_factory=list)
    stage_ids: list[str] = Field(default_factory=list)


# --- Module/File Types ---


class ModuleDefinition(BaseModel):
    """A module/interface/component definition from an .ato file."""

    name: str
    type: Literal["module", "interface", "component"]
    file: str
    entry: str
    line: Optional[int] = None
    super_type: Optional[str] = None


class FileTreeNode(BaseModel):
    """A node in the file tree."""

    name: str
    path: str
    type: Literal["file", "folder"]
    extension: Optional[str] = None
    children: Optional[list["FileTreeNode"]] = None


# --- Standard Library Types ---


class StdLibChild(BaseModel):
    """Child item in standard library."""

    name: str
    type: str
    item_type: str
    children: list["StdLibChild"] = Field(default_factory=list)


class StdLibItem(BaseModel):
    """Standard library item."""

    id: str
    name: str
    type: str
    description: str
    usage: Optional[str] = None
    children: list[StdLibChild] = Field(default_factory=list)
    parameters: list[dict] = Field(default_factory=list)


# --- BOM Types ---


class BOMParameter(BaseModel):
    """BOM component parameter."""

    name: str
    value: str
    unit: Optional[str] = None


class BOMUsage(BaseModel):
    """BOM component usage location."""

    address: str
    designator: str


class BOMComponent(BaseModel):
    """BOM component."""

    id: str
    lcsc: Optional[str] = None
    manufacturer: Optional[str] = None
    mpn: Optional[str] = None
    type: str
    value: str
    package: str
    description: Optional[str] = None
    quantity: int = 1
    unit_cost: Optional[float] = None
    stock: Optional[int] = None
    is_basic: Optional[bool] = None
    is_preferred: Optional[bool] = None
    source: str = "picked"
    parameters: list[BOMParameter] = Field(default_factory=list)
    usages: list[BOMUsage] = Field(default_factory=list)


class BOMData(BaseModel):
    """Bill of Materials data."""

    version: str = "1.0"
    components: list[BOMComponent] = Field(default_factory=list)


# --- Variables Types ---


class Variable(BaseModel):
    """A variable in the design."""

    name: str
    spec: Optional[str] = None
    spec_tolerance: Optional[str] = None
    actual: Optional[str] = None
    actual_tolerance: Optional[str] = None
    unit: Optional[str] = None
    type: str = "dimensionless"
    meets_spec: Optional[bool] = None
    source: Optional[str] = None


class VariableNode(BaseModel):
    """A node in the variable tree."""

    name: str
    type: Literal["module", "interface", "component"]
    path: str
    type_name: Optional[str] = None
    variables: Optional[list[Variable]] = None
    children: Optional[list["VariableNode"]] = None


class VariablesData(BaseModel):
    """Variables data for a build target."""

    version: str = "1.0"
    nodes: list[VariableNode] = Field(default_factory=list)


# --- Atopile Configuration ---


class DetectedInstallation(BaseModel):
    """A detected atopile installation."""

    path: str
    version: Optional[str] = None
    source: Literal["path", "venv", "manual"] = "path"


class InstallProgress(BaseModel):
    """Installation progress info."""

    message: str
    percent: Optional[float] = None


class AtopileConfig(BaseModel):
    """Atopile configuration state."""

    current_version: str = ""
    source: Literal["release", "branch", "local"] = "release"
    local_path: Optional[str] = None
    branch: Optional[str] = None
    available_versions: list[str] = Field(default_factory=list)
    available_branches: list[str] = Field(default_factory=list)
    detected_installations: list[DetectedInstallation] = Field(default_factory=list)
    is_installing: bool = False
    install_progress: Optional[InstallProgress] = None
    error: Optional[str] = None


# --- Log Counts ---


class LogCounts(BaseModel):
    """Log entry counts by level."""

    DEBUG: int = 0
    INFO: int = 0
    WARNING: int = 0
    ERROR: int = 0
    ALERT: int = 0


# --- Main AppState ---


class AppState(BaseModel):
    """
    THE SINGLE APP STATE - All state lives here.

    Python server owns this state and pushes it to all connected clients
    via WebSocket on every change.
    """

    # Connection
    is_connected: bool = True

    # Projects (from ato.yaml)
    projects: list[Project] = Field(default_factory=list)
    selected_project_root: Optional[str] = None
    selected_target_names: list[str] = Field(default_factory=list)

    # Builds (completed builds from /api/summary)
    builds: list[Build] = Field(default_factory=list)

    # Queued builds (from /api/builds/active)
    queued_builds: list[Build] = Field(default_factory=list)

    # Packages
    packages: list[PackageInfo] = Field(default_factory=list)
    is_loading_packages: bool = False
    packages_error: Optional[str] = None

    # Standard Library
    stdlib_items: list[StdLibItem] = Field(default_factory=list)
    is_loading_stdlib: bool = False

    # BOM
    bom_data: Optional[BOMData] = None
    is_loading_bom: bool = False
    bom_error: Optional[str] = None

    # Package details
    selected_package_details: Optional[PackageDetails] = None
    is_loading_package_details: bool = False
    package_details_error: Optional[str] = None

    # Build/Log selection
    selected_build_name: Optional[str] = None
    selected_project_name: Optional[str] = None
    selected_stage_ids: list[str] = Field(default_factory=list)
    log_entries: list[LogEntry] = Field(default_factory=list)
    is_loading_logs: bool = False
    log_file: Optional[str] = None

    # Log viewer UI
    enabled_log_levels: list[LogLevel] = Field(
        default_factory=lambda: ["INFO", "WARNING", "ERROR", "ALERT"]
    )
    log_search_query: str = ""
    log_timestamp_mode: Literal["absolute", "delta"] = "absolute"
    log_auto_scroll: bool = True

    # Log counts
    log_counts: Optional[LogCounts] = None
    log_total_count: Optional[int] = None
    log_has_more: Optional[bool] = None

    # Sidebar UI
    expanded_targets: list[str] = Field(default_factory=list)

    # Extension info
    version: str = "dev"
    logo_uri: str = ""

    # Atopile configuration
    atopile: AtopileConfig = Field(default_factory=AtopileConfig)

    # Problems
    problems: list[Problem] = Field(default_factory=list)
    is_loading_problems: bool = False
    problem_filter: ProblemFilter = Field(default_factory=ProblemFilter)

    # Project modules
    project_modules: dict[str, list[ModuleDefinition]] = Field(default_factory=dict)
    is_loading_modules: bool = False

    # Project files
    project_files: dict[str, list[FileTreeNode]] = Field(default_factory=dict)
    is_loading_files: bool = False

    # Variables
    current_variables_data: Optional[VariablesData] = None
    is_loading_variables: bool = False
    variables_error: Optional[str] = None

    class Config:
        # Use camelCase for JSON serialization to match frontend
        populate_by_name = True

    def to_frontend_dict(self) -> dict:
        """Convert to dict with camelCase keys for frontend compatibility."""
        # Get the dict representation
        data = self.model_dump()

        # Convert snake_case to camelCase
        def to_camel(s: str) -> str:
            components = s.split("_")
            return components[0] + "".join(x.title() for x in components[1:])

        def convert_keys(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {to_camel(k): convert_keys(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_keys(item) for item in obj]
            else:
                return obj

        return convert_keys(data)


# --- WebSocket State Manager ---


@dataclass
class ConnectedClient:
    """A connected WebSocket client."""

    client_id: str
    websocket: WebSocket
    subscribed: bool = True  # Whether to receive state updates


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

    async def set_projects(self, projects: list[Project]) -> None:
        """Update projects list."""
        self._state.projects = projects
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

    async def set_log_entries(self, entries: list[LogEntry]) -> None:
        """Update log entries."""
        self._state.log_entries = entries
        await self.broadcast_state()

    async def append_log_entries(self, entries: list[LogEntry]) -> None:
        """Append new log entries."""
        self._state.log_entries.extend(entries)
        await self.broadcast_state()

    async def set_selected_build(self, build_name: Optional[str]) -> None:
        """Set the selected build for log viewing."""
        self._state.selected_build_name = build_name
        await self.broadcast_state()

    async def set_enabled_log_levels(self, levels: list[LogLevel]) -> None:
        """Set enabled log levels."""
        self._state.enabled_log_levels = levels
        await self.broadcast_state()

    async def toggle_log_level(self, level: LogLevel) -> None:
        """Toggle a log level filter."""
        if level in self._state.enabled_log_levels:
            self._state.enabled_log_levels.remove(level)
        else:
            self._state.enabled_log_levels.append(level)
        await self.broadcast_state()

    async def set_log_search_query(self, query: str) -> None:
        """Set log search query."""
        self._state.log_search_query = query
        await self.broadcast_state()

    async def set_log_timestamp_mode(self, mode: Literal["absolute", "delta"]) -> None:
        """Set log timestamp mode."""
        self._state.log_timestamp_mode = mode
        await self.broadcast_state()

    async def toggle_log_timestamp_mode(self) -> None:
        """Toggle between absolute and delta timestamp modes."""
        self._state.log_timestamp_mode = (
            "delta" if self._state.log_timestamp_mode == "absolute" else "absolute"
        )
        await self.broadcast_state()

    async def set_log_auto_scroll(self, enabled: bool) -> None:
        """Set log auto-scroll."""
        self._state.log_auto_scroll = enabled
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

    async def set_variables_data(
        self, data: Optional[VariablesData], error: Optional[str] = None
    ) -> None:
        """Update variables data."""
        self._state.current_variables_data = data
        self._state.variables_error = error
        self._state.is_loading_variables = False
        await self.broadcast_state()

    async def set_log_counts(
        self,
        counts: Optional[LogCounts],
        total: Optional[int] = None,
        has_more: Optional[bool] = None,
    ) -> None:
        """Update log counts."""
        self._state.log_counts = counts
        self._state.log_total_count = total
        self._state.log_has_more = has_more
        await self.broadcast_state()

    # --- Action Handlers ---

    async def handle_action(self, action: str, payload: dict) -> dict:
        """
        Handle an action from a client.

        Returns a response dict with at least {"success": bool}.
        """
        try:
            if action == "selectProject":
                await self.set_selected_project(payload.get("projectRoot"))
                return {"success": True}

            elif action == "toggleTarget":
                await self.toggle_target(payload.get("targetName", ""))
                return {"success": True}

            elif action == "toggleTargetExpanded":
                await self.toggle_target_expanded(payload.get("targetName", ""))
                return {"success": True}

            elif action == "selectBuild":
                await self.set_selected_build(payload.get("buildName"))
                return {"success": True}

            elif action == "toggleLogLevel":
                level = payload.get("level")
                if level:
                    await self.toggle_log_level(level)
                return {"success": True}

            elif action == "setLogSearchQuery":
                await self.set_log_search_query(payload.get("query", ""))
                return {"success": True}

            elif action == "setLogTimestampMode":
                mode = payload.get("mode", "absolute")
                await self.set_log_timestamp_mode(mode)
                return {"success": True}

            elif action == "toggleLogTimestampMode":
                await self.toggle_log_timestamp_mode()
                return {"success": True}

            elif action == "setLogAutoScroll":
                await self.set_log_auto_scroll(payload.get("enabled", True))
                return {"success": True}

            else:
                log.warning(f"Unknown action: {action}")
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            log.error(f"Error handling action {action}: {e}")
            return {"success": False, "error": str(e)}


# Global singleton instance
server_state = ServerState()
