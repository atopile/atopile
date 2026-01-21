"""
FastAPI server for the build dashboard API.

Provides API endpoints for build data. The React frontend is served
directly by VS Code webview for better IDE integration.
"""

import asyncio
import hashlib
import json
import logging
import os
import queue
import socket
import sqlite3
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

import uvicorn
import yaml
from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from atopile.config import ProjectConfig
from atopile.server.core import launcher as core_launcher
from atopile.server.core import packages as core_packages
from atopile.server.core import projects as core_projects
from atopile.server.models import registry as registry_model
from atopile.server.stdlib import (
    StdLibItem,
    StdLibItemType,
    StdLibResponse,
    get_standard_library,
)
from atopile.server.state import server_state
from atopile.logging import get_central_log_db

log = logging.getLogger(__name__)


# --- Project Discovery Models ---


class BuildTarget(BaseModel):
    """A build target from ato.yaml"""

    name: str
    entry: str
    root: str


class Project(BaseModel):
    """A project discovered from ato.yaml"""

    root: str
    name: str
    targets: list[BuildTarget]


class ProjectsResponse(BaseModel):
    """Response for /api/projects endpoint"""

    projects: list[Project]
    total: int


# --- Build Models ---


class BuildRequest(BaseModel):
    """Request to start a build"""

    project_root: str
    targets: list[str] = []  # Empty = all targets
    frozen: bool = False
    # For standalone builds (entry point without ato.yaml build config)
    entry: str | None = None  # e.g., "main.ato:App" - if set, runs standalone build
    standalone: bool = False  # Whether to use standalone mode


class BuildResponse(BaseModel):
    """Response from build request"""

    success: bool
    message: str
    build_id: Optional[str] = None


class BuildStatusResponse(BaseModel):
    """Response for build status"""

    build_id: str
    status: str  # 'queued', 'building', 'success', 'warning', 'failed'
    project_root: str
    targets: list[str]
    return_code: Optional[int] = None
    error: Optional[str] = None


# --- Package Models ---


class InstalledPackage(BaseModel):
    """A package installed in a project (from ato.yaml dependencies)"""

    identifier: str  # e.g., "atopile/bosch-bme280"
    version: str  # e.g., "0.1.2"
    project_root: str  # Which project it's installed in


class PackageInfo(BaseModel):
    """Information about a package"""

    identifier: str  # e.g., "atopile/bosch-bme280"
    name: str  # e.g., "bosch-bme280"
    publisher: str  # e.g., "atopile"
    version: str | None = None  # Installed version (if installed)
    latest_version: str | None = None  # Latest available version
    description: str | None = None
    summary: str | None = None
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    installed: bool = False
    installed_in: list[str] = []  # List of project roots where installed
    # Stats from registry (may be None if not fetched)
    downloads: int | None = None
    version_count: int | None = None
    keywords: list[str] | None = None


class PackagesResponse(BaseModel):
    """Response for /api/packages endpoint"""

    packages: list[PackageInfo]
    total: int


class PackageActionRequest(BaseModel):
    """Request to install/update/remove a package"""

    package_identifier: str
    project_root: str
    version: str | None = None  # If None, installs latest


class PackageActionResponse(BaseModel):
    """Response from package action"""

    success: bool
    message: str
    action: str  # 'install', 'update', 'remove'


class RegistrySearchResponse(BaseModel):
    """Response for /api/registry/search endpoint"""

    packages: list[PackageInfo]
    total: int
    query: str


class PackageVersion(BaseModel):
    """Information about a package version/release"""

    version: str
    released_at: str | None = None
    requires_atopile: str | None = None
    size: int | None = None


class PackageDetails(BaseModel):
    """Detailed information about a package from the registry"""

    identifier: str
    name: str
    publisher: str
    version: str  # Latest version
    summary: str | None = None
    description: str | None = None
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    # Stats
    downloads: int | None = None
    downloads_this_week: int | None = None
    downloads_this_month: int | None = None
    # Versions
    versions: list[PackageVersion] = []
    version_count: int = 0
    # Installation status
    installed: bool = False
    installed_version: str | None = None
    installed_in: list[str] = []


# --- Package Summary Models (for unified packages panel endpoint) ---


class PackageSummaryItem(BaseModel):
    """Display-ready package info for the packages panel.

    This is the unified type sent from /api/packages/summary that merges
    installed package data with registry metadata.

    Note: Uses same field names as PackageInfo for frontend compatibility.
    """

    identifier: str  # e.g., "atopile/bosch-bme280"
    name: str  # e.g., "bosch-bme280"
    publisher: str  # e.g., "atopile"

    # Installation status (matches PackageInfo field names)
    installed: bool
    version: str | None = None  # Installed version (same as PackageInfo.version)
    installed_in: list[str] = []

    # Registry info (pre-merged)
    latest_version: str | None = None
    has_update: bool = False  # Pre-computed: version < latest_version

    # Display metadata
    summary: str | None = None
    description: str | None = None
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None

    # Stats
    downloads: int | None = None
    version_count: int | None = None
    keywords: list[str] = []


class RegistryStatus(BaseModel):
    """Status of the registry connection for error visibility."""

    available: bool
    error: str | None = None


class PackagesSummaryResponse(BaseModel):
    """Response for /api/packages/summary endpoint.

    Single response containing all data needed for the packages panel.
    """

    packages: list[PackageSummaryItem]
    total: int
    installed_count: int
    registry_status: RegistryStatus


# --- Problem Models ---


class Problem(BaseModel):
    """A problem (error or warning) from a build log"""

    id: str
    level: str  # 'error' | 'warning'
    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    stage: str | None = None
    logger: str | None = None
    build_name: str | None = None
    project_name: str | None = None
    timestamp: str | None = None
    ato_traceback: str | None = None
    exc_info: str | None = None


class ProblemsResponse(BaseModel):
    """Response for /api/problems endpoint"""

    problems: list[Problem]
    total: int
    error_count: int
    warning_count: int


# --- Module Discovery Models ---


class ModuleDefinition(BaseModel):
    """A module/interface/component definition from an .ato file"""

    name: str
    type: str  # 'module' | 'interface' | 'component'
    file: str  # Relative path to the .ato file
    entry: str  # Entry point format: "file.ato:ModuleName"
    line: int | None = None  # Line number where defined
    super_type: str | None = None  # Parent type if extends


class ModulesResponse(BaseModel):
    """Response for /api/modules endpoint"""

    modules: list[ModuleDefinition]
    total: int


class FileTreeNode(BaseModel):
    """A node in the file tree (either a file or folder)"""

    name: str
    path: str
    type: Literal["file", "folder"]
    extension: str | None = None  # 'ato' or 'py' for files
    children: list["FileTreeNode"] | None = None


class FilesResponse(BaseModel):
    """Response for /api/files endpoint"""

    files: list[FileTreeNode]
    total: int


class DependencyInfo(BaseModel):
    """A project dependency with version info"""

    identifier: str  # e.g., "atopile/resistors"
    version: str  # Installed version
    latest_version: str | None = None  # Latest available version
    name: str  # e.g., "resistors"
    publisher: str  # e.g., "atopile"
    repository: str | None = None
    has_update: bool = False


class DependenciesResponse(BaseModel):
    """Response for /api/dependencies endpoint"""

    dependencies: list[DependencyInfo]
    total: int


# --- WebSocket Connection Manager ---


@dataclass
class ClientSubscription:
    """Per-connection subscription state for WebSocket clients."""

    websocket: WebSocket
    log_filters: dict = field(default_factory=lambda: {"limit": 100})
    subscribed_channels: set = field(default_factory=set)
    last_log_id: int = 0  # Track last sent log for incremental updates


class ConnectionManager:
    """Manages WebSocket connections and per-connection filter state."""

    def __init__(self):
        self.clients: dict[WebSocket, ClientSubscription] = {}
        self._db_path: Optional[Path] = None
        self._logs_base: Optional[Path] = None

    def set_paths(self, db_path: Optional[Path], logs_base: Optional[Path]):
        """Set database and logs paths for querying."""
        self._db_path = db_path
        self._logs_base = logs_base

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.clients[websocket] = ClientSubscription(websocket=websocket)
        log.info(f"WebSocket client connected. Total clients: {len(self.clients)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected client."""
        self.clients.pop(websocket, None)
        log.info(f"WebSocket client disconnected. Total clients: {len(self.clients)}")

    async def handle_message(self, websocket: WebSocket, message: dict):
        """Handle an incoming message from a client."""
        client = self.clients.get(websocket)
        if not client:
            return

        action = message.get("action")
        channel = message.get("channel")

        if action == "subscribe":
            client.subscribed_channels.add(channel)
            if channel == "logs":
                client.log_filters = message.get("filters", {"limit": 100})
                await self.send_filtered_logs(client)
            elif channel == "summary":
                # Summary will be sent via broadcast when available
                pass
            elif channel == "problems":
                # Problems will be sent via broadcast when available
                pass
            elif channel == "builds":
                # Builds will be sent via broadcast when available
                pass

        elif action == "update_filter":
            if channel == "logs":
                client.log_filters = message.get("filters", {"limit": 100})
                client.last_log_id = 0  # Reset cursor on filter change
                log.info(f"WebSocket: update_filter for logs: {client.log_filters}")
                await self.send_filtered_logs(client)

        elif action == "unsubscribe":
            client.subscribed_channels.discard(channel)

    async def send_filtered_logs(self, client: ClientSubscription):
        """Query central log database with client's filters and send results."""
        log.info(f"send_filtered_logs called with db_path={self._db_path}")
        if not self._db_path or not self._db_path.exists():
            log.warning(f"Log DB not found at {self._db_path}, sending empty logs")
            await client.websocket.send_json(
                {"event": "logs", "data": {"logs": [], "total": 0, "has_more": False}}
            )
            return

        filters = client.log_filters
        try:
            conn = sqlite3.connect(str(self._db_path), timeout=5.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Build WHERE clause based on filters
            # Use new schema: logs JOIN builds
            conditions = []
            params: list = []

            # Handle build_name (format: "project:target" or just "target")
            if filters.get("build_name"):
                build_name = filters["build_name"]
                if ":" in build_name:
                    # Format: "project:target" - filter by both
                    project_part, target_part = build_name.split(":", 1)
                    conditions.append("builds.target = ?")
                    params.append(target_part)
                    conditions.append("builds.project_path LIKE ?")
                    params.append(f"%/{project_part}")
                else:
                    conditions.append("builds.target = ?")
                    params.append(build_name)

            # Handle project_name - match end of project_path
            if filters.get("project_name"):
                conditions.append("builds.project_path LIKE ?")
                params.append(f"%/{filters['project_name']}")

            # Handle multiple levels
            if filters.get("levels"):
                level_list = filters["levels"]
                if isinstance(level_list, str):
                    level_list = [lv.strip().upper() for lv in level_list.split(",")]
                placeholders = ",".join("?" * len(level_list))
                conditions.append(f"logs.level IN ({placeholders})")
                params.extend([lv.upper() for lv in level_list])

            # Search in message
            if filters.get("search"):
                conditions.append("logs.message LIKE ?")
                params.append(f"%{filters['search']}%")

            # Incremental fetch
            if filters.get("after_id"):
                conditions.append("logs.id > ?")
                params.append(filters["after_id"])

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            limit = filters.get("limit", 100)

            query = f"""
                SELECT logs.id, logs.build_id, logs.timestamp, logs.stage,
                       logs.level, logs.audience, logs.message,
                       logs.ato_traceback, logs.python_traceback,
                       builds.project_path, builds.target
                FROM logs
                JOIN builds ON logs.build_id = builds.build_id
                {where_clause}
                ORDER BY logs.id DESC
                LIMIT ?
            """
            params.append(limit)

            log.info(f"Executing query: {where_clause}, params={params}")
            cursor.execute(query, params)
            rows = cursor.fetchall()
            log.info(f"Query returned {len(rows)} rows")
            conn.close()

            # Convert to frontend-compatible format
            logs = []
            for row in reversed(rows):  # Reverse to chronological order
                logs.append(
                    {
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "stage": row["stage"],
                        "level": row["level"],
                        "message": row["message"],
                        "ato_traceback": row["ato_traceback"],
                        "python_traceback": row["python_traceback"],
                        "build_id": row["build_id"],
                        "target": row["target"],
                    }
                )

            if logs:
                client.last_log_id = logs[-1]["id"]

            await client.websocket.send_json(
                {
                    "event": "logs",
                    "data": {
                        "logs": logs,
                        "total": len(logs),
                        "has_more": len(logs) >= limit,
                    },
                }
            )

        except Exception as e:
            log.error(f"Error querying logs for WebSocket client: {e}")
            await client.websocket.send_json(
                {"event": "logs", "data": {"logs": [], "total": 0, "has_more": False}}
            )

    def log_matches_filter(self, log_entry: dict, filters: dict) -> bool:
        """Check if a log entry matches client's filter criteria."""
        # Check log levels
        if filters.get("levels"):
            level_list = filters["levels"]
            if isinstance(level_list, str):
                level_list = [lv.strip().upper() for lv in level_list.split(",")]
            entry_level = log_entry.get("level", "").upper()
            if entry_level not in [lv.upper() for lv in level_list]:
                return False

        # Check build_name (matches target and optionally project)
        if filters.get("build_name"):
            build_name = filters["build_name"]
            target = log_entry.get("target", "")
            project_path = log_entry.get("project_path", "")
            if ":" in build_name:
                # Format: "project:target" - check both
                project_part, target_part = build_name.split(":", 1)
                if target != target_part:
                    return False
                if not project_path.endswith(f"/{project_part}"):
                    return False
            else:
                if target != build_name:
                    return False

        # Check project_name (matches end of project_path)
        if filters.get("project_name"):
            project_path = log_entry.get("project_path", "")
            if not project_path.endswith(f"/{filters['project_name']}"):
                return False

        # Check search term
        if filters.get("search"):
            if filters["search"].lower() not in log_entry.get("message", "").lower():
                return False
        return True

    async def on_new_log(self, log_entry: dict):
        """Called when a new log is written - push to matching clients."""
        for client in list(self.clients.values()):
            if "logs" not in client.subscribed_channels:
                continue
            try:
                if self.log_matches_filter(log_entry, client.log_filters):
                    client.last_log_id = log_entry.get("id", 0)
                    await client.websocket.send_json(
                        {
                            "event": "logs",
                            "data": {
                                "logs": [log_entry],
                                "total": 1,
                                "incremental": True,
                            },
                        }
                    )
            except Exception as e:
                log.error(f"Error sending log to WebSocket client: {e}")
                self.disconnect(client.websocket)

    async def broadcast_to_channel(self, channel: str, event: str, data: dict):
        """Broadcast an event to all clients subscribed to a channel."""
        message = {"event": event, "data": data}
        for client in list(self.clients.values()):
            if channel in client.subscribed_channels:
                try:
                    await client.websocket.send_json(message)
                except Exception as e:
                    log.error(f"Error broadcasting to WebSocket client: {e}")
                    self.disconnect(client.websocket)

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Store reference to the main event loop for use in background threads."""
        self._main_loop = loop
        log.debug("Event loop stored for background thread broadcasts")

    def broadcast_sync(self, channel: str, event: str, data: dict):
        """
        Broadcast an event from synchronous code (e.g., background threads).

        This schedules the broadcast on the stored event loop.
        """
        # Use stored event loop (set during app startup)
        loop = getattr(self, "_main_loop", None)
        if loop is not None and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.broadcast_to_channel(channel, event, data), loop
            )
            return

        # Fallback: try to get current thread's event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.broadcast_to_channel(channel, event, data), loop
                )
            else:
                asyncio.run(self.broadcast_to_channel(channel, event, data))
        except RuntimeError:
            # No event loop available - log warning (this should be fixed)
            log.warning(f"No event loop available for broadcast: {event}")

    def on_new_log_sync(self, log_entry: dict):
        """
        Called when a new log is written from synchronous code.

        This schedules the log push on the stored event loop.
        """
        # Use stored event loop (set during app startup)
        loop = getattr(self, "_main_loop", None)
        if loop is not None and loop.is_running():
            asyncio.run_coroutine_threadsafe(self.on_new_log(log_entry), loop)
            return

        # Fallback: try to get current thread's event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.on_new_log(log_entry), loop)
            else:
                asyncio.run(self.on_new_log(log_entry))
        except RuntimeError:
            log.debug("No event loop available for log push")


# Global connection manager instance
ws_manager = ConnectionManager()


def extract_modules_from_file(
    ato_file: Path, project_root: Path
) -> list[ModuleDefinition]:
    """
    Extract all module/interface/component definitions from an .ato file.

    Uses the ANTLR parser to parse the file and extract BlockDefinitions.
    """
    return core_projects.extract_modules_from_file(ato_file, project_root)


def discover_modules_in_project(project_root: Path) -> list[ModuleDefinition]:
    """
    Discover all module definitions in a project by scanning .ato files.
    """
    return core_projects.discover_modules_in_project(project_root)


def parse_problems_from_log_file(
    log_file: Path, build_name: str, project_name: str | None = None
) -> list[Problem]:
    """
    Parse problems (warnings and errors) from a JSONL log file.

    Returns a list of Problem objects for all WARNING, ERROR, and ALERT log entries.
    """
    import re

    problems: list[Problem] = []

    if not log_file.exists():
        return problems

    # Skip SQLite database files - they're not JSONL log files
    if log_file.suffix == ".db":
        return problems

    try:
        content = log_file.read_text()
        lines = content.strip().split("\n")

        for i, line in enumerate(lines):
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            level = entry.get("level", "")
            if level not in ("WARNING", "ERROR", "ALERT"):
                continue

            # Parse source location from ato_traceback if available
            file_path = None
            line_num = None
            column = None

            ato_traceback = entry.get("ato_traceback", "")
            if ato_traceback:
                # Parse: File "path/file.ato", line 23, column 8
                match = re.search(
                    r'File "([^"]+)", line (\d+)(?:, column (\d+))?', ato_traceback
                )
                if match:
                    file_path = match.group(1)
                    line_num = int(match.group(2))
                    column = int(match.group(3)) if match.group(3) else None

            problems.append(
                Problem(
                    id=f"{build_name}-{i}",
                    level="warning" if level == "WARNING" else "error",
                    message=entry.get("message", ""),
                    file=file_path,
                    line=line_num,
                    column=column,
                    stage=entry.get("stage"),
                    logger=entry.get("logger"),
                    build_name=build_name,
                    project_name=project_name,
                    timestamp=entry.get("timestamp"),
                    ato_traceback=ato_traceback or None,
                    exc_info=entry.get("exc_info"),
                )
            )

    except Exception as e:
        log.warning(f"Failed to parse log file {log_file}: {e}")

    return problems


def _version_is_newer(installed: str | None, latest: str | None) -> bool:
    """
    Check if latest version is newer than installed version.

    Simple semver comparison - handles common version formats.
    Returns False if either version is None or comparison fails.
    """
    return registry_model.version_is_newer(installed, latest)


def search_registry_packages(query: str) -> list[PackageInfo]:
    """
    Search the package registry for packages matching the query.

    Uses the PackagesAPIClient to query the registry API.
    Results are cached for 5 minutes.
    """
    return registry_model.search_registry_packages(query)


def get_all_registry_packages() -> list[PackageInfo]:
    """
    Get all packages from the registry by querying multiple search terms.

    The registry API requires a search term (empty/wildcard returns 0 results).
    This function queries multiple terms and merges results to get all packages.
    Results are cached for 5 minutes.
    """
    return registry_model.get_all_registry_packages()


def get_package_details_from_registry(identifier: str) -> PackageDetails | None:
    """
    Get detailed package information from the registry.

    Fetches:
    - Full package info with stats (downloads)
    - List of releases (versions)
    """
    return registry_model.get_package_details_from_registry(identifier)


def get_installed_packages_for_project(project_root: Path) -> list[InstalledPackage]:
    """
    Read installed packages from a project's ato.yaml dependencies section.

    Supports two formats:
    1. List format (current):
       dependencies:
       - type: registry
         identifier: atopile/buttons
         release: 0.3.1

    2. Dict format (legacy):
       dependencies:
         "atopile/buttons": "0.3.1"
    """
    return core_packages.get_installed_packages_for_project(project_root)


def get_all_installed_packages(paths: list[Path]) -> dict[str, PackageInfo]:
    """
    Get all installed packages across all projects in the given paths.

    Returns a dict of package_identifier -> PackageInfo, with installed_in
    tracking which projects have each package.
    """
    return core_packages.get_all_installed_packages(paths)


def enrich_packages_with_registry(
    packages: dict[str, PackageInfo],
) -> dict[str, PackageInfo]:
    """
    Enrich installed packages with metadata from the registry.

    Fetches latest_version, summary, homepage, etc. from the registry
    for each installed package.
    """
    return registry_model.enrich_packages_with_registry(packages)


def _resolve_workspace_file(path_str: str, workspace_paths: list[Path]) -> Path | None:
    candidate = Path(path_str)
    if candidate.exists():
        return candidate

    if candidate.is_absolute():
        return None

    for root in workspace_paths:
        root_path = Path(root)
        try_path = root_path / candidate
        if try_path.exists():
            return try_path

    return None


def _resolve_entry_path(project_root: Path, entry: str | None) -> Path | None:
    if not entry:
        return None

    entry_file = entry.split(":")[0] if ":" in entry else entry
    entry_path = Path(entry_file)
    if not entry_path.is_absolute():
        entry_path = project_root / entry_file
    return entry_path


def _resolve_layout_path(project_root: Path, build_id: str) -> Path | None:
    candidates = [
        project_root / "layouts" / build_id / f"{build_id}.kicad_pcb",
        project_root / "layouts" / build_id,
        project_root / "layouts",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _resolve_3d_path(project_root: Path, build_id: str) -> Path | None:
    build_dir = project_root / "build" / "builds" / build_id
    if not build_dir.exists():
        return None

    candidate = build_dir / f"{build_id}.pcba.glb"
    if candidate.exists():
        return candidate

    glb_files = sorted(build_dir.glob("*.glb"))
    if glb_files:
        return glb_files[0]

    return build_dir


# Track active builds
_active_builds: dict[str, dict[str, Any]] = {}
_build_counter = 0
_build_lock = threading.Lock()

# Build history database
_build_history_db: Path | None = None

BUILD_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS build_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id TEXT UNIQUE NOT NULL,
    build_key TEXT NOT NULL,
    project_root TEXT NOT NULL,
    targets TEXT NOT NULL,
    entry TEXT,
    status TEXT NOT NULL,
    return_code INTEGER,
    error TEXT,
    started_at REAL NOT NULL,
    completed_at REAL,
    stages TEXT,
    warnings INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_build_history_project ON build_history(project_root);
CREATE INDEX IF NOT EXISTS idx_build_history_status ON build_history(status);
CREATE INDEX IF NOT EXISTS idx_build_history_started ON build_history(started_at DESC);
"""


def init_build_history_db(db_path: Path) -> None:
    """Initialize the build history SQLite database."""
    global _build_history_db
    _build_history_db = db_path

    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.executescript(BUILD_HISTORY_SCHEMA)
        conn.commit()
        conn.close()
        log.info(f"Initialized build history database: {db_path}")
    except Exception as e:
        log.error(f"Failed to initialize build history database: {e}")


def save_build_to_history(build_id: str, build_info: dict) -> None:
    """Save a build record to the history database."""
    if not _build_history_db:
        return

    try:
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        cursor = conn.cursor()

        # Count warnings/errors from stages
        stages = build_info.get("stages", [])
        warnings = sum(s.get("warnings", 0) for s in stages)
        errors = sum(s.get("errors", 0) for s in stages)

        cursor.execute(
            """
            INSERT OR REPLACE INTO build_history
            (build_id, build_key, project_root, targets, entry, status,
             return_code, error, started_at, completed_at, stages, warnings, errors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                build_id,
                build_info.get("build_key", ""),
                build_info.get("project_root", ""),
                json.dumps(build_info.get("targets", [])),
                build_info.get("entry"),
                build_info.get("status", "unknown"),
                build_info.get("return_code"),
                build_info.get("error"),
                build_info.get("started_at", time.time()),
                time.time(),  # completed_at
                json.dumps(stages),
                warnings,
                errors,
            ),
        )
        conn.commit()
        conn.close()
        log.debug(f"Saved build {build_id} to history")
    except Exception as e:
        log.error(f"Failed to save build to history: {e}")


def load_recent_builds_from_history(limit: int = 50) -> list[dict]:
    """Load recent builds from the history database."""
    if not _build_history_db or not _build_history_db.exists():
        return []

    try:
        conn = sqlite3.connect(str(_build_history_db), timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM build_history
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        builds = []
        for row in rows:
            builds.append(
                {
                    "build_id": row["build_id"],
                    "build_key": row["build_key"],
                    "project_root": row["project_root"],
                    "targets": json.loads(row["targets"]),
                    "entry": row["entry"],
                    "status": row["status"],
                    "return_code": row["return_code"],
                    "error": row["error"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "stages": json.loads(row["stages"]) if row["stages"] else [],
                    "warnings": row["warnings"],
                    "errors": row["errors"],
                }
            )
        return builds

    except Exception as e:
        log.error(f"Failed to load build history: {e}")
        return []


# Track active package operations
_active_package_ops: dict[str, dict[str, Any]] = {}
_package_op_counter = 0
_package_op_lock = threading.Lock()

# Build queue configuration
MAX_CONCURRENT_BUILDS = 4


def _make_build_key(project_root: str, targets: list[str], entry: str | None) -> str:
    """Create a unique key for a build configuration."""
    content = f"{project_root}:{':'.join(sorted(targets))}:{entry or 'default'}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _is_duplicate_build(build_key: str) -> str | None:
    """
    Check if a build with this key is already running or queued.

    Returns the existing build_id if duplicate, None otherwise.
    """
    with _build_lock:
        for build_id, build in _active_builds.items():
            if build.get("build_key") == build_key and build["status"] in (
                "queued",
                "building",
            ):
                return build_id
    return None


def _run_build_subprocess(
    build_id: str,
    project_root: str,
    targets: list[str],
    frozen: bool,
    entry: str | None,
    standalone: bool,
    result_q: queue.Queue,
    cancel_flags: dict[str, bool],
) -> None:
    """
    Run a single build in a subprocess and report progress.

    This function runs in a worker thread. It spawns an `ato build` subprocess
    and monitors it for completion while polling summary.json for stage updates.
    """
    # Send "started" message
    result_q.put(
        {
            "type": "started",
            "build_id": build_id,
            "project_root": project_root,
            "targets": targets,
        }
    )

    process = None
    final_stages: list[dict] = []
    error_msg: str | None = None
    return_code: int = -1

    try:
        # Build the command
        cmd = ["ato", "build", "--verbose"]

        # Determine the summary.json path for real-time monitoring
        summary_path = Path(project_root) / "build" / "logs" / "latest" / "summary.json"

        if standalone and entry:
            cmd.append(entry)
            cmd.append("--standalone")
            entry_file = entry.split(":")[0] if ":" in entry else entry
            entry_stem = Path(entry_file).stem
            standalone_dir = (
                Path(project_root) / f"standalone_{entry_stem}" / "build" / "logs"
            )
            standalone_dir.mkdir(parents=True, exist_ok=True)
            summary_path = standalone_dir.parent / "logs" / "latest" / "summary.json"
        else:
            for target in targets:
                cmd.extend(["--build", target])

        if frozen:
            cmd.append("--frozen")

        # Run the build subprocess
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        log.info(
            f"Build {build_id}: starting subprocess - cmd={' '.join(cmd)}, "
            f"cwd={project_root}, summary_path={summary_path}"
        )

        process = subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        # Poll for completion while monitoring summary.json
        last_stages: list[dict] = []
        poll_interval = 0.5
        stderr_output = ""

        while process.poll() is None:
            # Check for cancellation
            if cancel_flags.get(build_id, False):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                result_q.put(
                    {
                        "type": "cancelled",
                        "build_id": build_id,
                    }
                )
                return  # Exit the function after cancellation

            # Read summary.json for stage updates
            if summary_path.exists():
                try:
                    with open(summary_path, "r") as f:
                        summary = json.load(f)
                    # Find the build in summary using the helper function
                    current_build = _find_build_in_summary(summary, targets, entry)
                    if current_build:
                        current_stages = current_build.get("stages", [])
                        if current_stages != last_stages:
                            log.debug(
                                f"Build {build_id}: stage update - "
                                f"{len(current_stages)} stages"
                            )
                            result_q.put(
                                {
                                    "type": "stage",
                                    "build_id": build_id,
                                    "stages": current_stages,
                                }
                            )
                            last_stages = current_stages
                except (json.JSONDecodeError, IOError) as e:
                    log.debug(f"Build {build_id}: error reading summary.json: {e}")

            time.sleep(poll_interval)

        # Process completed
        return_code = process.returncode
        stderr_output = process.stderr.read() if process.stderr else ""

        # Get final stages from summary
        if summary_path.exists():
            try:
                with open(summary_path, "r") as f:
                    summary = json.load(f)
                final_build = _find_build_in_summary(summary, targets, entry)
                if final_build:
                    final_stages = final_build.get("stages", [])
            except (json.JSONDecodeError, IOError):
                pass

        if return_code != 0:
            error_msg = (
                stderr_output[:500]
                if stderr_output
                else f"Build failed with code {return_code}"
            )

    except Exception as e:
        error_msg = str(e)
        return_code = -1

    # Send completion message
    result_q.put(
        {
            "type": "completed",
            "build_id": build_id,
            "return_code": return_code,
            "error": error_msg,
            "stages": final_stages,
        }
    )


class BuildQueue:
    """
    Manages build execution with concurrency limiting using threading.

    Queues build requests and processes them in worker threads with subprocesses,
    respecting a maximum concurrent build limit. This approach is simpler than
    multiprocessing and matches the CLI's ParallelBuildManager pattern.
    """

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_BUILDS):
        # Pending builds - use list for reordering capability
        self._pending: list[str] = []
        self._pending_lock = threading.Lock()

        # Active builds tracking
        self._active: set[str] = set()
        self._active_lock = threading.Lock()

        self._max_concurrent = max_concurrent
        self._running = False

        # Thread pool for running builds
        self._executor: ThreadPoolExecutor | None = None

        # Result queue for worker threads to report back
        self._result_q: queue.Queue[dict[str, Any]] = queue.Queue()

        # Cancel flags (thread-safe dict for signaling cancellation)
        self._cancel_flags: dict[str, bool] = {}
        self._cancel_lock = threading.Lock()

        # Orchestrator thread
        self._orchestrator_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the thread pool and orchestrator thread."""
        if self._running:
            return

        self._running = True

        # Create thread pool executor
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_concurrent, thread_name_prefix="build-worker"
        )

        # Start orchestrator thread
        self._orchestrator_thread = threading.Thread(
            target=self._orchestrate, daemon=True
        )
        self._orchestrator_thread.start()
        log.info(f"BuildQueue: Started (max_concurrent={self._max_concurrent})")

    def enqueue(self, build_id: str) -> bool:
        """
        Add a build to the queue.

        Returns True if enqueued, False if already in queue/active.
        """
        with self._active_lock:
            if build_id in self._active:
                log.debug(f"BuildQueue: {build_id} already active, not enqueueing")
                return False

        with self._pending_lock:
            if build_id in self._pending:
                log.debug(f"BuildQueue: {build_id} already pending, not enqueueing")
                return False
            self._pending.append(build_id)
            log.debug(
                f"BuildQueue: Enqueued {build_id} "
                f"(pending={len(self._pending)}, active={len(self._active)})"
            )

        # Ensure workers are running
        if not self._running:
            self.start()
        return True

    def reorder(self, build_ids: list[str]) -> dict:
        """
        Reorder pending builds to match the given order.

        Args:
            build_ids: Desired order. Can include active build IDs - they're
                       ignored since active builds can't be reordered.

        Returns dict with:
            - reordered: list of build IDs that were reordered
            - already_active: list of build IDs that were already running
            - new_order: the resulting pending queue order
        """
        with self._active_lock:
            active_set = set(self._active)

        with self._pending_lock:
            # Separate active from pending in the requested order
            already_active = [bid for bid in build_ids if bid in active_set]
            reordered = [bid for bid in build_ids if bid in self._pending]

            # Add any pending builds not in the request (keep at end)
            remaining = [bid for bid in self._pending if bid not in build_ids]
            self._pending = reordered + remaining

            log.info(f"BuildQueue: Reordered queue to {self._pending}")
            return {
                "reordered": reordered,
                "already_active": already_active,
                "new_order": list(self._pending),
            }

    def move_to_position(self, build_id: str, position: int) -> dict:
        """
        Move a pending build to a specific position in the unified queue.

        The unified queue is: [active builds...] + [pending builds...]
        If the target position is among active builds (0 to n_active-1),
        the build is moved to the front of the pending queue (first to run next).

        Args:
            build_id: The build to move (must be pending, not active)
            position: Target position in the unified queue (0-indexed)

        Returns dict with:
            - success: whether the move succeeded
            - message: description of what happened
            - new_position: the actual position in the unified queue
            - new_pending_order: the resulting pending queue order
        """
        with self._active_lock:
            active_list = list(self._active)
            n_active = len(active_list)

            if build_id in self._active:
                return {
                    "success": False,
                    "message": "Cannot move an active build",
                    "new_position": None,
                    "new_pending_order": self.get_pending_order(),
                }

        with self._pending_lock:
            if build_id not in self._pending:
                return {
                    "success": False,
                    "message": "Build not found in pending queue",
                    "new_position": None,
                    "new_pending_order": list(self._pending),
                }

            # Remove from current position
            self._pending.remove(build_id)

            # Calculate target position in pending queue
            # If target is in the "active" zone, put at front of pending
            if position < n_active:
                pending_position = 0
            else:
                pending_position = min(position - n_active, len(self._pending))

            # Insert at new position
            self._pending.insert(pending_position, build_id)

            actual_position = n_active + pending_position
            log.info(
                f"BuildQueue: Moved {build_id} to position {actual_position} "
                f"(pending index {pending_position})"
            )

            return {
                "success": True,
                "message": f"Moved to position {actual_position}",
                "new_position": actual_position,
                "new_pending_order": list(self._pending),
            }

    def remove_pending(self, build_id: str) -> dict:
        """
        Remove a build from the pending queue.

        Returns dict with:
            - success: whether the build was found and removed
            - message: description of what happened
        Note: Cannot remove active builds - use cancel() for that.
        """
        with self._pending_lock:
            if build_id in self._pending:
                self._pending.remove(build_id)
                log.info(f"BuildQueue: Removed {build_id} from pending queue")
                return {"success": True, "message": "Removed from pending queue"}

        with self._active_lock:
            if build_id in self._active:
                return {
                    "success": False,
                    "message": "Build is active - use cancel() instead",
                }

        return {"success": False, "message": "Build not found in queue"}

    def get_queue_state(self) -> dict:
        """
        Return the full queue state for UI rendering.

        Returns dict with:
            - active: list of currently running build IDs (in no particular order)
            - pending: list of pending build IDs (in queue order)
            - max_concurrent: maximum concurrent builds
        """
        with self._active_lock:
            active = list(self._active)
        with self._pending_lock:
            pending = list(self._pending)
        return {
            "active": active,
            "pending": pending,
            "max_concurrent": self._max_concurrent,
        }

    def get_pending_order(self) -> list[str]:
        """Return the current order of pending builds."""
        with self._pending_lock:
            return list(self._pending)

    def _orchestrate(self) -> None:
        """
        Orchestrator loop - dispatch builds and apply results.

        Runs in a background thread, handling state updates and WebSocket broadcasts.
        """
        while self._running:
            # Apply any pending results from worker threads
            self._apply_results()

            # Dispatch next build if we have capacity
            self._dispatch_next()

            time.sleep(0.05)

    def _apply_results(self) -> None:
        """Apply results from worker threads."""
        while True:
            try:
                msg = self._result_q.get_nowait()
            except queue.Empty:
                break

            build_id = msg.get("build_id")
            msg_type = msg.get("type")

            if msg_type == "started":
                building_started_at = time.time()
                with _build_lock:
                    if build_id in _active_builds:
                        _active_builds[build_id]["status"] = "building"
                        _active_builds[build_id]["building_started_at"] = (
                            building_started_at
                        )

                ws_manager.broadcast_sync(
                    "builds",
                    "build:started",
                    {
                        "build_id": build_id,
                        "project_root": msg.get("project_root"),
                        "targets": msg.get("targets"),
                        "status": "building",
                        "building_started_at": building_started_at,
                    },
                )

                # Sync to server_state for /ws/state clients
                _sync_builds_to_state()

            elif msg_type == "stage":
                stages = msg.get("stages", [])
                with _build_lock:
                    if build_id in _active_builds:
                        _active_builds[build_id]["stages"] = stages

                ws_manager.broadcast_sync(
                    "builds",
                    "build:stage",
                    {"build_id": build_id, "stages": stages},
                )

                # Sync to server_state for /ws/state clients
                _sync_builds_to_state()

            elif msg_type == "completed":
                return_code = msg.get("return_code", -1)
                error = msg.get("error")
                stages = msg.get("stages", [])
                status = "success" if return_code == 0 else "failed"
                duration = 0.0

                with _build_lock:
                    if build_id in _active_builds:
                        started_at = _active_builds[build_id].get(
                            "building_started_at"
                        ) or _active_builds[build_id].get("started_at")
                        if started_at:
                            duration = time.time() - started_at
                        _active_builds[build_id]["status"] = status
                        _active_builds[build_id]["return_code"] = return_code
                        _active_builds[build_id]["error"] = error
                        _active_builds[build_id]["stages"] = stages
                        _active_builds[build_id]["duration"] = duration

                        # Count warnings/errors from stages
                        warnings = sum(
                            1 for s in stages if s.get("status") == "warning"
                        )
                        errors = sum(1 for s in stages if s.get("status") == "error")
                        _active_builds[build_id]["warnings"] = warnings
                        _active_builds[build_id]["errors"] = errors

                with self._active_lock:
                    self._active.discard(build_id)

                with self._cancel_lock:
                    self._cancel_flags.pop(build_id, None)

                ws_manager.broadcast_sync(
                    "builds",
                    "build:completed",
                    {
                        "build_id": build_id,
                        "status": status,
                        "return_code": return_code,
                        "error": error,
                        "stages": stages,
                        "duration": duration,
                    },
                )

                # Sync to server_state for /ws/state clients
                _sync_builds_to_state()

                # Refresh problems from logs after build completes
                _sync_problems_to_state()

                # Save to history
                with _build_lock:
                    if build_id in _active_builds:
                        save_build_to_history(build_id, _active_builds[build_id])

                log.info(f"BuildQueue: Build {build_id} completed with status {status}")

            elif msg_type == "cancelled":
                with _build_lock:
                    if build_id in _active_builds:
                        _active_builds[build_id]["status"] = "cancelled"

                with self._active_lock:
                    self._active.discard(build_id)

                with self._cancel_lock:
                    self._cancel_flags.pop(build_id, None)

                ws_manager.broadcast_sync(
                    "builds",
                    "build:cancelled",
                    {"build_id": build_id},
                )

                # Sync to server_state for /ws/state clients
                _sync_builds_to_state()

    def _dispatch_next(self) -> None:
        """Dispatch next pending build if capacity available."""
        if not self._executor:
            return

        with self._active_lock:
            if len(self._active) >= self._max_concurrent:
                return

        # Get next build from pending list
        with self._pending_lock:
            if not self._pending:
                return

            build_id = self._pending.pop(0)

        # Check if build was cancelled while pending
        with _build_lock:
            if build_id not in _active_builds:
                log.debug(f"BuildQueue: {build_id} no longer exists, skipping")
                return
            if _active_builds[build_id].get("status") == "cancelled":
                log.debug(f"BuildQueue: {build_id} was cancelled, skipping")
                return
            build_info = _active_builds[build_id].copy()

        with self._active_lock:
            self._active.add(build_id)

        with self._cancel_lock:
            self._cancel_flags[build_id] = False

        log.info(
            f"BuildQueue: Dispatching {build_id} "
            f"(active={len(self._active)}/{self._max_concurrent})"
        )

        # Submit task to thread pool
        self._executor.submit(
            _run_build_subprocess,
            build_id,
            build_info["project_root"],
            build_info["targets"],
            build_info.get("frozen", False),
            build_info.get("entry"),
            build_info.get("standalone", False),
            self._result_q,
            self._cancel_flags,
        )

    def cancel(self, build_id: str) -> dict:
        """
        Cancel a build - either remove from pending or signal worker to stop.

        Returns dict with:
            - success: whether the cancellation was initiated
            - message: description of what happened
            - was_pending: True if removed from pending, False if was active
        """
        # First try to remove from pending queue
        result = self.remove_pending(build_id)
        if result["success"]:
            return {
                "success": True,
                "message": "Removed from pending queue",
                "was_pending": True,
            }

        # If active, signal cancellation
        with self._active_lock:
            if build_id in self._active:
                with self._cancel_lock:
                    self._cancel_flags[build_id] = True
                return {
                    "success": True,
                    "message": "Cancellation signal sent to active build",
                    "was_pending": False,
                }

        return {
            "success": False,
            "message": "Build not found in queue",
            "was_pending": False,
        }

    def stop(self) -> None:
        """Stop thread pool and orchestrator thread."""
        self._running = False

        # Signal all active builds to cancel
        with self._cancel_lock:
            for build_id in list(self._cancel_flags.keys()):
                self._cancel_flags[build_id] = True

        # Wait for orchestrator
        if self._orchestrator_thread and self._orchestrator_thread.is_alive():
            self._orchestrator_thread.join(timeout=2.0)
        self._orchestrator_thread = None

        # Shutdown thread pool
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    def clear(self) -> None:
        """Clear the queue and active set. Used for testing."""
        self.stop()
        with self._pending_lock:
            self._pending.clear()
        with self._active_lock:
            self._active.clear()
        with self._cancel_lock:
            self._cancel_flags.clear()

    def get_status(self) -> dict:
        """Return current queue status for debugging."""
        with self._pending_lock:
            pending_count = len(self._pending)
        with self._active_lock:
            active_count = len(self._active)
            active_builds = list(self._active)
        return {
            "pending_count": pending_count,
            "active_count": active_count,
            "active_builds": active_builds,
            "max_concurrent": self._max_concurrent,
            "orchestrator_running": self._running,
        }

    def get_max_concurrent(self) -> int:
        """Return the current max concurrent builds limit."""
        return self._max_concurrent

    def set_max_concurrent(self, value: int) -> None:
        """
        Set the max concurrent builds limit.

        With ThreadPoolExecutor, we need to recreate the executor to change
        the max workers. This is done lazily - the new limit takes effect
        for new dispatches.
        """
        new_max = max(1, value)
        old_max = self._max_concurrent
        self._max_concurrent = new_max
        log.info(f"BuildQueue: max_concurrent changed from {old_max} to {new_max}")

        # Recreate executor with new max workers if running
        if self._running and self._executor:
            # Don't shutdown existing executor - let running tasks complete
            # Create new executor for future tasks
            self._executor = ThreadPoolExecutor(
                max_workers=new_max, thread_name_prefix="build-worker"
            )


# Get the default max concurrent (CPU count)
_DEFAULT_MAX_CONCURRENT = os.cpu_count() or 4

# Global build queue instance - starts with default (CPU count)
_build_queue = BuildQueue(max_concurrent=_DEFAULT_MAX_CONCURRENT)

# Settings state
_build_settings = {
    "use_default_max_concurrent": True,
    "custom_max_concurrent": _DEFAULT_MAX_CONCURRENT,
}


def _get_state_builds():
    """
    Convert _active_builds to StateBuild objects.

    Helper function used by both sync and async state sync functions.
    """
    from atopile.server.state import Build as StateBuild, BuildStage as StateStage

    with _build_lock:
        state_builds = []
        for build_id, build_info in _active_builds.items():
            # Convert stages if present
            stages = None
            if build_info.get("stages"):
                stages = [
                    StateStage(
                        name=s.get("name", ""),
                        stage_id=s.get("stage_id", s.get("name", "")),
                        display_name=s.get("display_name"),
                        elapsed_seconds=s.get("elapsed_seconds", 0.0),
                        status=s.get("status", "pending"),
                        infos=s.get("infos", 0),
                        warnings=s.get("warnings", 0),
                        errors=s.get("errors", 0),
                        alerts=s.get("alerts", 0),
                    )
                    for s in build_info["stages"]
                ]

            # Determine display name and build name
            # name is used by frontend to match builds to targets
            entry = build_info.get("entry")
            targets = build_info.get("targets", [])
            if entry:
                display_name = entry.split(":")[-1] if ":" in entry else entry
                build_name = display_name
            elif targets:
                display_name = ", ".join(targets)
                build_name = targets[0] if len(targets) == 1 else display_name
            else:
                display_name = "Build"
                build_name = build_id

            state_builds.append(
                StateBuild(
                    name=build_name,
                    display_name=display_name,
                    build_id=build_id,
                    project_name=Path(build_info.get("project_root", "")).name,
                    status=build_info.get("status", "queued"),
                    elapsed_seconds=build_info.get("duration", 0.0),
                    warnings=build_info.get("warnings", 0),
                    errors=build_info.get("errors", 0),
                    return_code=build_info.get("return_code"),
                    error=build_info.get("error"),  # Include error message
                    project_root=build_info.get("project_root"),
                    targets=targets,
                    entry=entry,
                    started_at=build_info.get("started_at"),
                    stages=stages,
                )
            )
        return state_builds


def _sync_builds_to_state():
    """
    Sync _active_builds to server_state for WebSocket broadcast.

    Called when build status changes (from background thread).
    Uses asyncio.run_coroutine_threadsafe to schedule on main event loop.
    """
    state_builds = _get_state_builds()
    queued_builds = [b for b in state_builds if b.status in ("queued", "building")]

    # Schedule async state update on main event loop
    loop = server_state._event_loop
    if loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(server_state.set_builds(state_builds), loop)
        asyncio.run_coroutine_threadsafe(
            server_state.set_queued_builds(queued_builds), loop
        )
    else:
        log.warning("Cannot sync builds to state: event loop not available")


async def _sync_builds_to_state_async():
    """
    Async version of _sync_builds_to_state.

    Called from async contexts (like WebSocket handlers) where we want
    to await the state update rather than scheduling it.
    """
    state_builds = _get_state_builds()
    # Set all builds
    await server_state.set_builds(state_builds)
    # Set queued builds (active builds only for queue panel)
    queued_builds = [b for b in state_builds if b.status in ("queued", "building")]
    await server_state.set_queued_builds(queued_builds)


def _sync_problems_to_state():
    """
    Sync problems to server_state for WebSocket broadcast.

    Called after build completes to update problems from log files.
    Uses asyncio.run_coroutine_threadsafe to schedule on main event loop.
    """
    loop = server_state._event_loop
    if loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(_sync_problems_to_state_async(), loop)
    else:
        log.warning("Cannot sync problems to state: event loop not available")


async def _sync_problems_to_state_async():
    """
    Async function to refresh problems from build logs.

    Reads problems from all project build logs and updates server_state.
    """
    from atopile.server.state import Problem as StateProblem

    workspace_paths = server_state._workspace_paths
    if not workspace_paths:
        return

    try:
        projects = discover_projects_in_paths(workspace_paths)
        all_problems: list[StateProblem] = []

        for project in projects:
            project_path = Path(project.root)
            project_summary = (
                project_path / "build" / "logs" / "latest" / "summary.json"
            )

            if not project_summary.exists():
                continue

            try:
                summary_data = json.loads(project_summary.read_text())
                builds_data = summary_data.get("builds", [])

                for build in builds_data:
                    log_file_path = build.get("log_file")
                    if not log_file_path:
                        continue

                    log_file = Path(log_file_path)
                    if not log_file.exists():
                        continue

                    # Parse problems from log
                    build_problems = parse_problems_from_log_file(
                        log_file,
                        build_name=build.get("name", ""),
                        project_name=project.name,
                    )

                    # Convert to state types
                    for p in build_problems:
                        all_problems.append(
                            StateProblem(
                                id=p.id,
                                level=p.level,
                                message=p.message,
                                file=p.file,
                                line=p.line,
                                column=p.column,
                                stage=p.stage,
                                logger=p.logger,
                                build_name=p.build_name,
                                project_name=p.project_name,
                                timestamp=p.timestamp,
                                ato_traceback=p.ato_traceback,
                                exc_info=p.exc_info,
                            )
                        )
            except Exception as e:
                log.warning(f"Failed to read problems from {project_summary}: {e}")

        await server_state.set_problems(all_problems)
        log.info(f"Refreshed problems after build: {len(all_problems)} problems found")
    except Exception as e:
        log.error(f"Failed to refresh problems: {e}")


async def _refresh_packages_async():
    """Refresh packages and update server_state. Called after install/remove.

    This mirrors the logic from the refreshPackages action handler to ensure
    we get ALL packages (installed + registry), not just installed ones.
    """
    from atopile.server.state import PackageInfo as StatePackageInfo

    scan_paths = server_state._workspace_paths
    if not scan_paths:
        return

    try:
        packages_map: dict[str, StatePackageInfo] = {}
        registry_error: str | None = None

        # 1. Get installed packages
        installed = get_all_installed_packages(scan_paths)
        for pkg in installed.values():
            packages_map[pkg.identifier] = StatePackageInfo(
                identifier=pkg.identifier,
                name=pkg.name,
                publisher=pkg.publisher,
                version=pkg.version,
                installed=True,
                installed_in=pkg.installed_in,
            )

        # 2. Get ALL registry packages (uses multiple search terms)
        try:
            registry_packages = get_all_registry_packages()
            log.info(
                f"[_refresh_packages_async] Registry returned {len(registry_packages)} packages"
            )

            # Merge registry data into packages_map
            for reg_pkg in registry_packages:
                if reg_pkg.identifier in packages_map:
                    # Update installed package with registry metadata
                    existing = packages_map[reg_pkg.identifier]
                    packages_map[reg_pkg.identifier] = StatePackageInfo(
                        identifier=existing.identifier,
                        name=existing.name,
                        publisher=existing.publisher,
                        version=existing.version,
                        latest_version=reg_pkg.latest_version,
                        description=reg_pkg.description or reg_pkg.summary,
                        summary=reg_pkg.summary,
                        homepage=reg_pkg.homepage,
                        repository=reg_pkg.repository,
                        license=reg_pkg.license,
                        installed=True,
                        installed_in=existing.installed_in,
                        has_update=_version_is_newer(
                            existing.version, reg_pkg.latest_version
                        ),
                        downloads=reg_pkg.downloads,
                        version_count=reg_pkg.version_count,
                        keywords=reg_pkg.keywords or [],
                    )
                else:
                    # Add uninstalled registry package
                    packages_map[reg_pkg.identifier] = StatePackageInfo(
                        identifier=reg_pkg.identifier,
                        name=reg_pkg.name,
                        publisher=reg_pkg.publisher,
                        latest_version=reg_pkg.latest_version,
                        description=reg_pkg.description or reg_pkg.summary,
                        summary=reg_pkg.summary,
                        homepage=reg_pkg.homepage,
                        repository=reg_pkg.repository,
                        license=reg_pkg.license,
                        installed=False,
                        installed_in=[],
                        has_update=False,
                        downloads=reg_pkg.downloads,
                        version_count=reg_pkg.version_count,
                        keywords=reg_pkg.keywords or [],
                    )

        except Exception as e:
            registry_error = str(e)
            log.warning(f"[_refresh_packages_async] Registry fetch failed: {e}")

        # Sort: installed first, then alphabetically
        state_packages = sorted(
            packages_map.values(),
            key=lambda p: (not p.installed, p.identifier.lower()),
        )

        await server_state.set_packages(list(state_packages), registry_error)
        log.info(
            f"Refreshed packages after install/remove: {len(state_packages)} packages"
        )
    except Exception as e:
        log.error(f"Failed to refresh packages: {e}")


def _find_build_in_summary(
    summary: dict, targets: list[str], entry: str | None = None
) -> dict | None:
    """Find the current build in the summary.json data."""
    builds = summary.get("builds", [])
    if not builds:
        return None

    # If we have specific targets, try to match by name
    if targets:
        for build in builds:
            if build.get("name") in targets:
                return build

    # If we have an entry point, try to match by entry
    if entry:
        for build in builds:
            if entry in build.get("entry", ""):
                return build

    # Fallback: return the first/most recent build
    return builds[0] if builds else None


def _broadcast_stage_changes(
    build_id: str, last_stages: list[dict], new_stages: list[dict]
) -> None:
    """Broadcast stage changes to WebSocket clients."""
    # Find newly completed stages or stages with updated status
    last_stage_map = {s.get("name"): s for s in last_stages}

    for stage in new_stages:
        stage_name = stage.get("name")
        old_stage = last_stage_map.get(stage_name)

        # New stage or status changed
        if not old_stage or old_stage.get("status") != stage.get("status"):
            ws_manager.broadcast_sync(
                "builds",
                "build:stage",
                {
                    "build_id": build_id,
                    "stage": stage,
                },
            )


def cancel_build(build_id: str) -> bool:
    """
    Cancel a running build.

    Returns True if the build was cancelled, False if not found or already completed.
    """
    with _build_lock:
        if build_id not in _active_builds:
            return False

        build_info = _active_builds[build_id]

        # Check if already completed
        if build_info["status"] not in ("queued", "building"):
            return False

        # Mark as cancelled in the build record
        build_info["status"] = "cancelled"
        build_info["error"] = "Build cancelled by user"

    # Signal the BuildQueue to cancel the build
    # This will either remove it from pending or signal the worker thread
    result = _build_queue.cancel(build_id)

    # If it was pending (not yet started), we need to broadcast cancellation
    # (active builds will broadcast when the worker detects the cancel flag)
    if result.get("was_pending"):
        ws_manager.broadcast_sync(
            "builds",
            "build:cancelled",
            {"build_id": build_id},
        )

    log.info(f"Build {build_id} cancelled")
    return True


def discover_projects_in_paths(paths: list[Path]) -> list[Project]:
    """
    Discover all ato projects in the given paths.

    For each path:
    - If it contains ato.yaml, treat it as a single project
    - Otherwise, recursively find all ato.yaml files

    Returns list of Project objects with their build targets.
    """
    return core_projects.discover_projects_in_paths(paths)


def create_app(
    summary_file: Optional[Path] = None,
    logs_base: Optional[Path] = None,
    workspace_paths: Optional[list[Path]] = None,
) -> FastAPI:
    """
    Create the FastAPI application with API routes for the dashboard.

    Args:
        summary_file: Path to summary.json file.
        logs_base: Base directory for logs.
        workspace_paths: List of workspace paths to scan for projects.
    """
    app = FastAPI(title="atopile Build Server")

    # Add CORS middleware to allow requests from VS Code webview
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Webviews use vscode-webview:// origin
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Track the current state
    state: dict[str, Any] = {
        "summary_file": summary_file,
        "logs_base": logs_base,
        "workspace_paths": workspace_paths or [],
    }

    # Set up WebSocket manager with central log database path
    db_path = get_central_log_db()
    ws_manager.set_paths(db_path, logs_base)

    # Define populate_initial_state first (before startup handler calls it)
    async def populate_initial_state():
        """Populate server state with projects and packages on startup."""
        scan_paths = state["workspace_paths"]
        if not scan_paths:
            log.info("No workspace paths configured, skipping initial state population")
            return

        log.info(f"Populating initial state from {len(scan_paths)} workspace paths")

        # Import state types
        from atopile.server.state import Project as StateProject
        from atopile.server.state import BuildTarget as StateBuildTarget
        from atopile.server.state import PackageInfo as StatePackageInfo

        # Discover and set projects
        try:
            projects = discover_projects_in_paths(scan_paths)
            state_projects = [
                StateProject(
                    root=p.root,
                    name=p.name,
                    targets=[
                        StateBuildTarget(name=t.name, entry=t.entry, root=t.root)
                        for t in p.targets
                    ],
                )
                for p in projects
            ]
            await server_state.set_projects(state_projects)
            log.info(f"Loaded {len(state_projects)} projects")
        except Exception as e:
            log.error(f"Failed to load projects: {e}")

        # Discover and set packages
        try:
            installed = get_all_installed_packages(scan_paths)
            enriched = enrich_packages_with_registry(installed)

            state_packages = [
                StatePackageInfo(
                    identifier=p.identifier,
                    name=p.name,
                    publisher=p.publisher,
                    version=p.version,
                    latest_version=p.latest_version,
                    description=p.description,
                    summary=p.summary,
                    homepage=p.homepage,
                    repository=p.repository,
                    license=p.license,
                    installed=p.installed,
                    installed_in=p.installed_in,
                    has_update=_version_is_newer(p.version, p.latest_version),
                    downloads=p.downloads,
                    version_count=p.version_count,
                    keywords=p.keywords or [],
                )
                for p in enriched.values()
            ]
            await server_state.set_packages(state_packages)
            log.info(f"Loaded {len(state_packages)} packages")
        except Exception as e:
            log.error(f"Failed to load packages: {e}")

    # Capture event loop on startup for background thread broadcasts
    @app.on_event("startup")
    async def capture_event_loop():
        """Store the main event loop for use in background threads."""
        loop = asyncio.get_running_loop()
        ws_manager.set_event_loop(loop)
        server_state.set_event_loop(loop)
        server_state.set_workspace_paths(state["workspace_paths"])
        log.info("Event loop captured for WebSocket broadcasts")

        # Populate initial state with projects and packages
        await populate_initial_state()

    # Initialize build history database
    if logs_base:
        build_history_db_path = logs_base / "build_history.db"
        init_build_history_db(build_history_db_path)

    # --- WebSocket Endpoint ---

    @app.websocket("/ws/events")
    async def websocket_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for real-time event streaming.

        Clients can subscribe to channels (builds, logs, summary, problems)
        and receive filtered updates in real-time.
        """
        await ws_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_json()
                await ws_manager.handle_message(websocket, data)
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
        except Exception as e:
            log.error(f"WebSocket error: {e}")
            ws_manager.disconnect(websocket)

    async def handle_data_action(action: str, payload: dict) -> dict:
        """Handle data-fetching actions that need access to server.py functions."""
        global _package_op_counter, _build_counter

        log.info(f"handle_data_action called: action={action}, payload={payload}")

        try:
            if action == "refreshProjects":
                # Discover projects and update state
                scan_paths = state["workspace_paths"]
                if scan_paths:
                    from atopile.server.state import Project as StateProject
                    from atopile.server.state import BuildTarget as StateBuildTarget

                    projects = discover_projects_in_paths(scan_paths)
                    # Convert to state types
                    state_projects = [
                        StateProject(
                            root=p.root,
                            name=p.name,
                            targets=[
                                StateBuildTarget(
                                    name=t.name, entry=t.entry, root=t.root
                                )
                                for t in p.targets
                            ],
                        )
                        for p in projects
                    ]
                    await server_state.set_projects(state_projects)
                return {"success": True}

            elif action == "createProject":
                parent_directory = payload.get("parentDirectory")
                name = payload.get("name")

                if not parent_directory:
                    workspace_paths = state.get("workspace_paths", [])
                    if workspace_paths:
                        parent_directory = str(workspace_paths[0])
                    else:
                        return {"success": False, "error": "Missing parentDirectory"}

                try:
                    project_dir, project_name = core_projects.create_project(
                        Path(parent_directory), name
                    )
                except ValueError as e:
                    return {"success": False, "error": str(e)}

                await handle_data_action("refreshProjects", {})
                return {
                    "success": True,
                    "project_root": str(project_dir),
                    "project_name": project_name,
                }

            elif action == "refreshPackages":
                # Fetch ALL packages: installed + registry
                # This mirrors the logic from /api/packages/summary endpoint
                from atopile.server.state import PackageInfo as StatePackageInfo

                packages_map: dict[str, StatePackageInfo] = {}
                scan_paths = state.get("workspace_paths", [])
                registry_error: str | None = None

                # 1. Get installed packages
                if scan_paths:
                    installed = get_all_installed_packages(scan_paths)
                    for pkg in installed.values():
                        packages_map[pkg.identifier] = StatePackageInfo(
                            identifier=pkg.identifier,
                            name=pkg.name,
                            publisher=pkg.publisher,
                            version=pkg.version,
                            installed=True,
                            installed_in=pkg.installed_in,
                        )

                # 2. Get ALL registry packages (uses multiple search terms)
                try:
                    registry_packages = get_all_registry_packages()
                    log.info(
                        f"[refreshPackages] Registry returned {len(registry_packages)} packages"
                    )

                    # Merge registry data into packages_map
                    for reg_pkg in registry_packages:
                        if reg_pkg.identifier in packages_map:
                            # Update installed package with registry metadata
                            existing = packages_map[reg_pkg.identifier]
                            packages_map[reg_pkg.identifier] = StatePackageInfo(
                                identifier=existing.identifier,
                                name=existing.name,
                                publisher=existing.publisher,
                                version=existing.version,
                                latest_version=reg_pkg.latest_version,
                                description=reg_pkg.description or reg_pkg.summary,
                                summary=reg_pkg.summary,
                                homepage=reg_pkg.homepage,
                                repository=reg_pkg.repository,
                                license=reg_pkg.license,
                                installed=True,
                                installed_in=existing.installed_in,
                                has_update=_version_is_newer(
                                    existing.version, reg_pkg.latest_version
                                ),
                                downloads=reg_pkg.downloads,
                                version_count=reg_pkg.version_count,
                                keywords=reg_pkg.keywords or [],
                            )
                        else:
                            # Add uninstalled registry package
                            packages_map[reg_pkg.identifier] = StatePackageInfo(
                                identifier=reg_pkg.identifier,
                                name=reg_pkg.name,
                                publisher=reg_pkg.publisher,
                                latest_version=reg_pkg.latest_version,
                                description=reg_pkg.description or reg_pkg.summary,
                                summary=reg_pkg.summary,
                                homepage=reg_pkg.homepage,
                                repository=reg_pkg.repository,
                                license=reg_pkg.license,
                                installed=False,
                                installed_in=[],
                                has_update=False,
                                downloads=reg_pkg.downloads,
                                version_count=reg_pkg.version_count,
                                keywords=reg_pkg.keywords or [],
                            )

                except Exception as e:
                    registry_error = str(e)
                    log.warning(f"[refreshPackages] Registry fetch failed: {e}")

                # Sort: installed first, then alphabetically
                state_packages = sorted(
                    packages_map.values(),
                    key=lambda p: (not p.installed, p.identifier.lower()),
                )

                log.info(
                    f"[refreshPackages] Setting {len(state_packages)} total packages"
                )
                await server_state.set_packages(list(state_packages), registry_error)
                return {"success": True}

            elif action == "refreshStdlib":
                # Fetch stdlib
                from atopile.server.state import StdLibItem as StateStdLibItem

                items = get_standard_library()
                # Convert - StdLibItem is similar between modules
                # Note: get_standard_library() returns a list directly, not an object with .items
                state_items = [
                    StateStdLibItem(
                        id=item.id,
                        name=item.name,
                        type=item.type,
                        description=item.description,
                        usage=item.usage,
                        children=[],  # Simplified
                        parameters=[],
                    )
                    for item in items
                ]
                await server_state.set_stdlib_items(state_items)
                return {"success": True}

            elif action == "buildPackage":
                package_id = payload.get("packageId", "")
                entry = payload.get("entry")

                if not package_id:
                    return {"success": False, "error": "Missing packageId"}

                return await handle_data_action(
                    "build",
                    {
                        "projectRoot": package_id,
                        "entry": entry,
                        "standalone": entry is not None,
                    },
                )

            elif action == "build":
                # Support multiple payload formats:
                # 1. Backend: { projectRoot, targets, entry?, standalone?, frozen? }
                # 2. Frontend: { level, id, label } - level determines meaning of id
                # 3. REST-style: { project_root, targets }
                #
                # Frontend level meanings:
                # - level='project': id is project root path, build all targets
                # - level='build': id is project root, buildId or label is target name
                # - level='symbol': id is project root, build specific entry

                project_root = payload.get("projectRoot") or payload.get(
                    "project_root", ""
                )
                targets = payload.get("targets", [])
                entry = payload.get("entry")
                standalone = payload.get("standalone", False)
                frozen = payload.get("frozen", False)
                level = payload.get("level")
                payload_id = payload.get("id")
                payload_label = payload.get("label")

                log.info(
                    f"Build action: level={level}, id={payload_id}, label={payload_label}, targets={targets}"
                )

                # Handle frontend level/id/label format
                # Flag to indicate we should build all targets from ato.yaml
                build_all_targets = False
                if level and payload_id:
                    if level == "project":
                        # id is the project root, build all targets from ato.yaml
                        project_root = payload_id
                        # For project-level build, we'll read all targets from ato.yaml later
                        if not targets:
                            build_all_targets = True
                        log.info(
                            f"Build project: {project_root}, build_all_targets={build_all_targets}"
                        )
                    elif level == "build":
                        # Frontend sends id as "${projectId}:${targetName}"
                        # For projects: projectId is filesystem path
                        # For packages: projectId is package identifier (e.g., "atopile/package-name")
                        if ":" in payload_id:
                            # Split from the right to handle paths that might contain colons (Windows)
                            parts = payload_id.rsplit(":", 1)
                            project_root = parts[0]
                            # If label not provided, use the parsed target
                            if not payload_label and len(parts) > 1:
                                payload_label = parts[1]
                        else:
                            project_root = payload_id

                        if payload_label and not targets:
                            targets = [payload_label]
                        log.info(f"Build target: {targets} in {project_root}")
                    elif level == "symbol":
                        # id is project root, entry should be set
                        project_root = payload_id
                        log.info(f"Build symbol: {entry} in {project_root}")

                # If no projectRoot provided, try to use selected project from state
                if not project_root:
                    project_root = server_state._state.selected_project_root or ""
                    log.info(f"Using selected project from state: {project_root}")

                # If no targets provided, try to use selected targets from state
                if not targets:
                    targets = server_state._state.selected_target_names or []
                    log.info(f"Using selected targets from state: {targets}")

                # Validate project path - if not a valid path, try to resolve as package identifier
                project_path = Path(project_root) if project_root else Path("")
                log.info(
                    f"Validating project path: {project_path}, exists={project_path.exists() if project_root else False}"
                )
                if project_root and not project_path.exists():
                    # Check if this looks like a package identifier (e.g., "atopile/package-name")
                    if "/" in project_root and not project_root.startswith("/"):
                        package_identifier = project_root
                        log.info(
                            f"Project root looks like package identifier: {package_identifier}"
                        )
                        # Look up the package in state to find its installed_in paths
                        packages = server_state._state.packages or []
                        pkg = next(
                            (p for p in packages if p.identifier == package_identifier),
                            None,
                        )
                        if pkg and pkg.installed_in:
                            # Find the package's actual directory within the installed project
                            # Packages are installed at: {project_root}/.ato/modules/{identifier}/
                            consuming_project = pkg.installed_in[0]
                            package_dir = (
                                Path(consuming_project)
                                / ".ato"
                                / "modules"
                                / package_identifier
                            )
                            if package_dir.exists():
                                log.info(
                                    f"Resolved package {package_identifier} to package dir: {package_dir}"
                                )
                                project_root = str(package_dir)
                                project_path = package_dir
                            else:
                                # Fallback to the consuming project (for backwards compatibility)
                                log.warning(
                                    f"Package dir {package_dir} not found, using project: {consuming_project}"
                                )
                                project_root = consuming_project
                                project_path = Path(project_root)
                        else:
                            log.warning(
                                f"Package {package_identifier} not found in state or not installed anywhere"
                            )

                if not project_root or not project_path.exists():
                    log.warning(
                        f"Build failed: Project path does not exist: {project_root}"
                    )
                    return {
                        "success": False,
                        "error": f"Project path does not exist: {project_root}",
                    }

                # Validate ato.yaml or entry for standalone
                if standalone:
                    if not entry:
                        return {
                            "success": False,
                            "error": "Standalone builds require an entry point",
                        }
                    entry_file = entry.split(":")[0] if ":" in entry else entry
                    entry_path = project_path / entry_file
                    if not entry_path.exists():
                        return {
                            "success": False,
                            "error": f"Entry file not found: {entry_path}",
                        }
                else:
                    ato_yaml_path = project_path / "ato.yaml"
                    log.info(
                        f"Checking for ato.yaml: {ato_yaml_path}, exists={ato_yaml_path.exists()}"
                    )
                    if not ato_yaml_path.exists():
                        log.warning(
                            f"Build failed: No ato.yaml found in: {project_root}"
                        )
                        return {
                            "success": False,
                            "error": f"No ato.yaml found in: {project_root}",
                        }

                    # If build_all_targets is set, read all targets from ato.yaml
                    if build_all_targets:
                        try:
                            # Use atopile's ProjectConfig to parse ato.yaml properly
                            project_config = ProjectConfig.from_path(project_path)
                            all_targets = (
                                list(project_config.builds.keys())
                                if project_config
                                else []
                            )
                            if all_targets:
                                log.info(
                                    f"Found {len(all_targets)} targets in ato.yaml: {all_targets}"
                                )
                                # Queue a separate build for each target
                                build_ids = []
                                for target_name in all_targets:
                                    # Check for duplicate
                                    target_build_key = _make_build_key(
                                        project_root, [target_name], entry
                                    )
                                    existing_id = _is_duplicate_build(target_build_key)
                                    if existing_id:
                                        log.info(
                                            f"Target {target_name} already building: {existing_id}"
                                        )
                                        build_ids.append(existing_id)
                                        continue

                                    # Generate build ID for this target
                                    with _build_lock:
                                        global _build_counter
                                        _build_counter += 1
                                        build_id = (
                                            f"build-{_build_counter}-{int(time.time())}"
                                        )

                                        # Register the build
                                        _active_builds[build_id] = {
                                            "status": "queued",
                                            "project_root": project_root,
                                            "targets": [target_name],
                                            "entry": entry,
                                            "standalone": standalone,
                                            "frozen": frozen,
                                            "build_key": target_build_key,
                                            "return_code": None,
                                            "error": None,
                                            "started_at": time.time(),
                                            "stages": [],
                                        }

                                    # Enqueue the build
                                    log.info(
                                        f"Enqueueing build for target {target_name}: {build_id}"
                                    )
                                    _build_queue.enqueue(build_id)
                                    build_ids.append(build_id)

                                # Sync to server_state for WebSocket broadcast
                                await _sync_builds_to_state_async()
                                log.info(
                                    f"Queued {len(build_ids)} builds for project: {project_root}"
                                )

                                return {
                                    "success": True,
                                    "message": f"Queued {len(build_ids)} builds for all targets",
                                    "build_ids": build_ids,
                                    "targets": all_targets,
                                }
                            else:
                                # No targets found, fall back to default
                                log.info(
                                    "No targets found in ato.yaml, falling back to 'default'"
                                )
                                targets = ["default"]
                        except Exception as e:
                            log.warning(
                                f"Failed to read targets from ato.yaml: {e}, falling back to 'default'"
                            )
                            targets = ["default"]

                # Check for duplicate builds
                build_key = _make_build_key(project_root, targets, entry)
                existing_build_id = _is_duplicate_build(build_key)
                if existing_build_id:
                    return {
                        "success": True,
                        "message": "Build already in progress",
                        "build_id": existing_build_id,
                    }

                # Generate build ID
                build_label = entry if standalone else "project"
                with _build_lock:
                    _build_counter += 1
                    build_id = f"build-{_build_counter}-{int(time.time())}"

                    # Register the build
                    _active_builds[build_id] = {
                        "status": "queued",
                        "project_root": project_root,
                        "targets": targets,
                        "entry": entry,
                        "standalone": standalone,
                        "frozen": frozen,
                        "build_key": build_key,
                        "return_code": None,
                        "error": None,
                        "started_at": time.time(),
                        "stages": [],
                    }

                # Enqueue the build
                log.info(f"Enqueueing build: {build_id}")
                _build_queue.enqueue(build_id)
                log.info(f"Build enqueued: {build_id}")

                # Sync to server_state for WebSocket broadcast (use async version)
                await _sync_builds_to_state_async()
                log.info(f"Build state synced to WebSocket clients")

                log.info(f"Build queued via WebSocket: {build_id} for {build_label}")
                return {
                    "success": True,
                    "message": f"Build queued for {build_label}",
                    "build_id": build_id,
                }

            elif action == "cancelBuild":
                build_id = payload.get("buildId", "")
                if not build_id:
                    return {"success": False, "error": "Missing buildId"}

                if build_id not in _active_builds:
                    return {"success": False, "error": f"Build not found: {build_id}"}

                success = cancel_build(build_id)
                if success:
                    log.info(f"Build cancelled via WebSocket: {build_id}")
                    return {"success": True, "message": f"Build {build_id} cancelled"}
                else:
                    return {
                        "success": False,
                        "message": f"Build {build_id} cannot be cancelled (already completed)",
                    }

            elif action == "fetchModules":
                project_root = payload.get("projectRoot", "")
                if project_root:
                    from atopile.server.state import (
                        ModuleDefinition as StateModuleDefinition,
                    )

                    modules = discover_modules_in_project(Path(project_root))
                    state_modules = [
                        StateModuleDefinition(
                            name=m.name,
                            type=m.type,
                            file=m.file,
                            entry=m.entry,
                            line=m.line,
                            super_type=m.super_type,
                        )
                        for m in modules
                    ]
                    await server_state.set_project_modules(project_root, state_modules)
                return {"success": True}

            elif action == "getPackageDetails":
                package_id = payload.get("packageId", "")
                if package_id:
                    from atopile.server.state import (
                        PackageDetails as StatePackageDetails,
                    )

                    details = get_package_details_from_registry(package_id)
                    if details:
                        state_details = StatePackageDetails(
                            identifier=details.identifier,
                            name=details.name,
                            publisher=details.publisher,
                            version=details.version,
                            summary=details.summary,
                            description=details.description,
                            homepage=details.homepage,
                            repository=details.repository,
                            license=details.license,
                            downloads=details.downloads,
                            downloads_this_week=details.downloads_this_week,
                            downloads_this_month=details.downloads_this_month,
                            versions=[],  # Simplified
                            version_count=details.version_count,
                            installed=details.installed,
                            installed_version=details.installed_version,
                            installed_in=details.installed_in,
                        )
                        await server_state.set_package_details(state_details)
                    else:
                        await server_state.set_package_details(
                            None, f"Package not found: {package_id}"
                        )
                return {"success": True}

            elif action == "clearPackageDetails":
                await server_state.set_package_details(None)
                return {"success": True}

            elif action == "refreshBOM":
                # Fetch BOM for a project/target
                project_root = payload.get("projectRoot", "")
                target = payload.get("target", "default")

                if not project_root:
                    # Use selected project if not specified
                    selected = server_state._state.selected_project_root
                    if selected:
                        project_root = selected

                if not project_root:
                    await server_state.set_bom_data(None, "No project selected")
                    return {"success": False, "error": "No project selected"}

                project_path = Path(project_root)
                bom_path = (
                    project_path / "build" / "builds" / target / f"{target}.bom.json"
                )

                if not bom_path.exists():
                    await server_state.set_bom_data(
                        None, f"BOM not found. Run build first."
                    )
                    return {"success": True, "info": "BOM not found"}

                try:
                    from atopile.server.state import BOMData

                    bom_json = json.loads(bom_path.read_text())
                    # BOM data is generic JSON, pass it through
                    await server_state.set_bom_data(bom_json)
                    return {"success": True}
                except Exception as e:
                    await server_state.set_bom_data(None, str(e))
                    return {"success": False, "error": str(e)}

            elif action == "refreshProblems":
                # Fetch problems from all projects
                from atopile.server.state import Problem as StateProblem

                workspace_paths = state.get("workspace_paths", [])
                projects = discover_projects_in_paths(workspace_paths)
                all_problems: list[StateProblem] = []

                for project in projects:
                    project_path = Path(project.root)
                    project_summary = (
                        project_path / "build" / "logs" / "latest" / "summary.json"
                    )

                    if not project_summary.exists():
                        continue

                    try:
                        summary_data = json.loads(project_summary.read_text())
                        builds_data = summary_data.get("builds", [])

                        for build in builds_data:
                            log_file_path = build.get("log_file")
                            if not log_file_path:
                                continue

                            log_file = Path(log_file_path)
                            if not log_file.exists():
                                continue

                            # Parse problems from log
                            build_problems = parse_problems_from_log_file(
                                log_file,
                                build_name=build.get("name", ""),
                                project_name=project.name,
                            )

                            # Convert to state types
                            for p in build_problems:
                                all_problems.append(
                                    StateProblem(
                                        id=p.id,
                                        level=p.level,
                                        message=p.message,
                                        file=p.file,
                                        line=p.line,
                                        column=p.column,
                                        stage=p.stage,
                                        logger=p.logger,
                                        build_name=p.build_name,
                                        project_name=p.project_name,
                                        timestamp=p.timestamp,
                                        ato_traceback=p.ato_traceback,
                                        exc_info=p.exc_info,
                                    )
                                )
                    except Exception as e:
                        log.warning(
                            f"Failed to read problems from {project_summary}: {e}"
                        )

                await server_state.set_problems(all_problems)
                return {"success": True}

            elif action == "fetchVariables":
                # Fetch variables for a project/target
                project_root = payload.get("projectRoot", "")
                target = payload.get("target", "default")

                if not project_root:
                    await server_state.set_variables_data(None, "No project specified")
                    return {"success": False, "error": "No project specified"}

                project_path = Path(project_root)
                variables_path = (
                    project_path
                    / "build"
                    / "builds"
                    / target
                    / f"{target}.variables.json"
                )

                if not variables_path.exists():
                    await server_state.set_variables_data(
                        None, "Variables not found. Run build first."
                    )
                    return {"success": True, "info": "Variables not found"}

                try:
                    variables_json = json.loads(variables_path.read_text())
                    await server_state.set_variables_data(variables_json)
                    return {"success": True}
                except Exception as e:
                    await server_state.set_variables_data(None, str(e))
                    return {"success": False, "error": str(e)}

            elif action == "installPackage":
                # Install a package into a project
                package_id = payload.get("packageId", "")
                project_root = payload.get("projectRoot", "")
                version = payload.get("version")

                if not package_id or not project_root:
                    return {
                        "success": False,
                        "error": "Missing packageId or projectRoot",
                    }

                project_path = Path(project_root)
                if not project_path.exists():
                    return {
                        "success": False,
                        "error": f"Project not found: {project_root}",
                    }

                if not (project_path / "ato.yaml").exists():
                    return {
                        "success": False,
                        "error": f"No ato.yaml in: {project_root}",
                    }

                # Generate operation ID
                with _package_op_lock:
                    _package_op_counter += 1
                    op_id = f"pkg-install-{_package_op_counter}-{int(time.time())}"

                    _active_package_ops[op_id] = {
                        "action": "install",
                        "status": "running",
                        "package": package_id,
                        "project_root": project_root,
                        "error": None,
                    }

                # Build command
                cmd = ["ato", "add", package_id]
                if version:
                    cmd.append(f"@{version}")

                # Run in thread
                def run_install():
                    try:
                        result = subprocess.run(
                            cmd,
                            cwd=project_root,
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )
                        with _package_op_lock:
                            if result.returncode == 0:
                                _active_package_ops[op_id]["status"] = "success"
                                # Refresh packages after install
                                loop = server_state._event_loop
                                if loop and loop.is_running():
                                    asyncio.run_coroutine_threadsafe(
                                        _refresh_packages_async(), loop
                                    )
                            else:
                                _active_package_ops[op_id]["status"] = "failed"
                                _active_package_ops[op_id]["error"] = result.stderr[
                                    :500
                                ]
                    except Exception as e:
                        with _package_op_lock:
                            _active_package_ops[op_id]["status"] = "failed"
                            _active_package_ops[op_id]["error"] = str(e)

                import threading

                threading.Thread(target=run_install, daemon=True).start()

                log.info(f"Package install started via WebSocket: {package_id}")
                return {
                    "success": True,
                    "message": f"Installing {package_id}...",
                    "op_id": op_id,
                }

            elif action == "changeDependencyVersion":
                package_id = payload.get("identifier") or payload.get("packageId", "")
                project_root = payload.get("projectRoot") or payload.get("projectId", "")
                version = payload.get("version")

                if not package_id or not project_root or not version:
                    return {
                        "success": False,
                        "error": "Missing identifier, projectRoot, or version",
                    }

                return await handle_data_action(
                    "installPackage",
                    {
                        "packageId": package_id,
                        "projectRoot": project_root,
                        "version": version,
                    },
                )

            elif action == "removePackage":
                # Remove a package from a project
                package_id = payload.get("packageId", "")
                project_root = payload.get("projectRoot", "")

                if not package_id or not project_root:
                    return {
                        "success": False,
                        "error": "Missing packageId or projectRoot",
                    }

                project_path = Path(project_root)
                if not project_path.exists():
                    return {
                        "success": False,
                        "error": f"Project not found: {project_root}",
                    }

                # Generate operation ID
                with _package_op_lock:
                    _package_op_counter += 1
                    op_id = f"pkg-remove-{_package_op_counter}-{int(time.time())}"

                    _active_package_ops[op_id] = {
                        "action": "remove",
                        "status": "running",
                        "package": package_id,
                        "project_root": project_root,
                        "error": None,
                    }

                # Build command
                cmd = ["ato", "remove", package_id]

                # Run in thread
                def run_remove():
                    try:
                        result = subprocess.run(
                            cmd,
                            cwd=project_root,
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )
                        with _package_op_lock:
                            if result.returncode == 0:
                                _active_package_ops[op_id]["status"] = "success"
                                # Refresh packages after remove
                                loop = server_state._event_loop
                                if loop and loop.is_running():
                                    asyncio.run_coroutine_threadsafe(
                                        _refresh_packages_async(), loop
                                    )
                            else:
                                _active_package_ops[op_id]["status"] = "failed"
                                _active_package_ops[op_id]["error"] = result.stderr[
                                    :500
                                ]
                    except Exception as e:
                        with _package_op_lock:
                            _active_package_ops[op_id]["status"] = "failed"
                            _active_package_ops[op_id]["error"] = str(e)

                import threading

                threading.Thread(target=run_remove, daemon=True).start()

                log.info(f"Package remove started via WebSocket: {package_id}")
                return {
                    "success": True,
                    "message": f"Removing {package_id}...",
                    "op_id": op_id,
                }

            elif action == "fetchFiles":
                # Fetch file tree for a project
                project_root = payload.get("projectRoot", "")
                if not project_root:
                    return {"success": True, "info": "No project specified"}

                project_path = Path(project_root)
                if not project_path.exists():
                    return {
                        "success": False,
                        "error": f"Project not found: {project_root}",
                    }

                file_tree = core_projects.build_file_tree(project_path, project_path)
                await server_state.set_project_files(project_root, file_tree)
                return {"success": True}

            elif action == "fetchDependencies":
                # Fetch dependencies for a project from ato.yaml
                project_root = payload.get("projectRoot", "")
                if not project_root:
                    return {"success": True, "info": "No project specified"}

                project_path = Path(project_root)
                if not project_path.exists():
                    return {
                        "success": False,
                        "error": f"Project not found: {project_root}",
                    }

                from atopile.server.state import DependencyInfo

                # Get installed packages for this project
                installed = get_installed_packages_for_project(project_path)

                # Convert to DependencyInfo objects with latest version info
                dependencies: list[DependencyInfo] = []
                for pkg in installed:
                    # Parse identifier to get publisher and name
                    parts = pkg.identifier.split("/")
                    publisher = parts[0] if len(parts) > 1 else "unknown"
                    name = parts[-1]

                    # Try to get latest version from cached packages
                    latest_version = None
                    has_update = False
                    repository = None

                    cached_pkg = server_state.packages_by_id.get(pkg.identifier)
                    if cached_pkg:
                        latest_version = cached_pkg.latest_version
                        has_update = registry_model.version_is_newer(
                            pkg.version, latest_version
                        )
                        repository = cached_pkg.repository

                    dependencies.append(
                        DependencyInfo(
                            identifier=pkg.identifier,
                            version=pkg.version,
                            latest_version=latest_version,
                            name=name,
                            publisher=publisher,
                            repository=repository,
                            has_update=has_update,
                        )
                    )

                await server_state.set_project_dependencies(project_root, dependencies)
                return {"success": True}

            elif action == "openFile":
                file_path = payload.get("file")
                line = payload.get("line")
                column = payload.get("column")

                if not file_path:
                    return {"success": False, "error": "Missing file path"}

                workspace_paths = state.get("workspace_paths", [])
                resolved = _resolve_workspace_file(file_path, workspace_paths)
                if not resolved:
                    return {
                        "success": False,
                        "error": f"File not found: {file_path}",
                    }

                line_num = None
                column_num = None
                try:
                    if line is not None:
                        line_num = int(line)
                    if column is not None:
                        column_num = int(column)
                except (TypeError, ValueError):
                    pass

                core_launcher.open_in_editor(
                    resolved,
                    line=line_num,
                    column=column_num,
                )
                return {"success": True}

            elif action == "openSource":
                project_root = payload.get("projectId", "")
                entry = payload.get("entry")
                if not project_root or not entry:
                    return {"success": False, "error": "Missing projectId or entry"}

                project_path = Path(project_root)
                entry_path = _resolve_entry_path(project_path, entry)
                if not entry_path or not entry_path.exists():
                    return {"success": False, "error": f"Entry not found: {entry}"}

                core_launcher.open_in_editor(entry_path)
                return {"success": True}

            elif action == "openKiCad":
                project_root = payload.get("projectId", "")
                build_id = payload.get("buildId", "")
                if not project_root or not build_id:
                    return {"success": False, "error": "Missing projectId or buildId"}

                project_path = Path(project_root)
                target = _resolve_layout_path(project_path, build_id)
                if not target:
                    return {"success": False, "error": "Layout not found"}

                core_launcher.open_with_system(target)
                return {"success": True}

            elif action == "openLayout":
                project_root = payload.get("projectId", "")
                build_id = payload.get("buildId", "")
                if not project_root or not build_id:
                    return {"success": False, "error": "Missing projectId or buildId"}

                project_path = Path(project_root)
                target = _resolve_layout_path(project_path, build_id)
                if not target:
                    return {"success": False, "error": "Layout not found"}

                core_launcher.open_with_system(target)
                return {"success": True}

            elif action == "open3D":
                project_root = payload.get("projectId", "")
                build_id = payload.get("buildId", "")
                if not project_root or not build_id:
                    return {"success": False, "error": "Missing projectId or buildId"}

                project_path = Path(project_root)
                target = _resolve_3d_path(project_path, build_id)
                if not target:
                    return {"success": False, "error": "3D model not found"}

                core_launcher.open_with_system(target)
                return {"success": True}

            elif action == "getMaxConcurrentSetting":
                # Return current max concurrent build settings
                return {
                    "success": True,
                    "setting": {
                        "use_default": _build_settings["use_default_max_concurrent"],
                        "custom_value": _build_settings["custom_max_concurrent"],
                        "default_value": _DEFAULT_MAX_CONCURRENT,
                        "current_value": _build_queue.get_max_concurrent(),
                    },
                }

            elif action == "setMaxConcurrentSetting":
                # Update max concurrent build settings
                use_default = payload.get("useDefault", True)
                custom_value = payload.get("customValue")

                _build_settings["use_default_max_concurrent"] = use_default

                if use_default:
                    _build_queue.set_max_concurrent(_DEFAULT_MAX_CONCURRENT)
                elif custom_value is not None:
                    # Clamp value to reasonable range
                    custom = max(1, min(32, int(custom_value)))
                    _build_settings["custom_max_concurrent"] = custom
                    _build_queue.set_max_concurrent(custom)

                return {
                    "success": True,
                    "setting": {
                        "use_default": _build_settings["use_default_max_concurrent"],
                        "custom_value": _build_settings["custom_max_concurrent"],
                        "default_value": _DEFAULT_MAX_CONCURRENT,
                        "current_value": _build_queue.get_max_concurrent(),
                    },
                }

            elif action == "selectBuild":
                # Select a build and load its logs
                build_name = payload.get("buildName")
                project_name = payload.get("projectName")
                from atopile.server.state import LogEntry as StateLogEntry

                # Update selected build name in state
                await server_state.set_selected_build(build_name)

                # Clear existing logs first
                await server_state.set_log_entries([])

                # If no build selected, just return
                if not build_name:
                    log.info("[selectBuild] No build selected, cleared logs")
                    return {"success": True}

                # Find the build's log file
                log_file_path = None
                with _build_lock:
                    for bid, build_info in _active_builds.items():
                        if build_info.get("display_name") == build_name:
                            log_file_path = build_info.get("log_file")
                            break

                # Also check summary.json for completed builds
                if not log_file_path:
                    workspace_paths = state.get("workspace_paths", [])
                    for ws_path in workspace_paths:
                        summary_path = (
                            Path(ws_path) / "build" / "logs" / "latest" / "summary.json"
                        )
                        if summary_path.exists():
                            try:
                                summary = json.loads(summary_path.read_text())
                                for build in summary.get("builds", []):
                                    if (
                                        build.get("name") == build_name
                                        or build.get("display_name") == build_name
                                    ):
                                        log_file_path = build.get("log_file")
                                        break
                            except Exception:
                                pass
                        if log_file_path:
                            break

                if not log_file_path or not Path(log_file_path).exists():
                    log.warning(
                        f"[selectBuild] Log file not found for build: {build_name}"
                    )
                    return {"success": True, "info": "Log file not found"}

                # Parse log entries from JSONL file
                log_entries: list[StateLogEntry] = []
                try:
                    log_file = Path(log_file_path)
                    content = log_file.read_text()
                    for line in content.strip().split("\n"):
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                            log_entries.append(
                                StateLogEntry(
                                    timestamp=entry.get("timestamp", ""),
                                    level=entry.get("level", "INFO"),
                                    message=entry.get("message", ""),
                                    logger=entry.get("logger", ""),
                                    stage=entry.get("stage"),
                                    ato_traceback=entry.get("ato_traceback"),
                                    exc_info=entry.get("exc_info"),
                                )
                            )
                        except json.JSONDecodeError:
                            continue

                    await server_state.set_log_entries(log_entries)
                    log.info(
                        f"[selectBuild] Loaded {len(log_entries)} log entries for {build_name}"
                    )

                except Exception as e:
                    log.error(f"[selectBuild] Failed to load logs: {e}")
                    return {"success": False, "error": str(e)}

                return {"success": True, "log_count": len(log_entries)}

            else:
                # Not a data action, let state.py handle it
                return None

        except Exception as e:
            log.error(f"Error handling data action {action}: {e}")
            return {"success": False, "error": str(e)}

    @app.websocket("/ws/state")
    async def websocket_state_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for full AppState push.

        This is the primary endpoint for the new thin-client architecture:
        - On connect: sends full AppState immediately
        - On state change: broadcasts full AppState to all clients
        - Receives actions: handles client actions and updates state

        Message format:
        - Server -> Client: {"type": "state", "data": <AppState>}
        - Client -> Server: {"type": "action", "action": "<action>", "payload": {...}}
        - Server -> Client: {"type": "action_result", "success": bool, "error"?: string}
        """
        client_id = await server_state.connect_client(websocket)
        log.info(f"WebSocket state client connected: {client_id}")
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                log.info(f"WebSocket state received: type={msg_type}, data={data}")

                if msg_type == "action":
                    action = data.get("action", "")
                    # Support both formats:
                    # 1. { type, action, payload: {...} } - backend format
                    # 2. { type, action, key1, key2, ... } - frontend format (no payload wrapper)
                    if "payload" in data:
                        payload = data["payload"]
                    else:
                        # Extract everything except type and action as payload
                        payload = {
                            k: v for k, v in data.items() if k not in ("type", "action")
                        }
                    log.info(f"Processing action: {action}, payload: {payload}")

                    # Try data actions first (need access to server.py functions)
                    result = await handle_data_action(action, payload)
                    if result is None:
                        # Not a data action, let state.py handle it
                        result = await server_state.handle_action(action, payload)

                    await websocket.send_json({"type": "action_result", **result})

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                else:
                    log.debug(f"Unknown message type from {client_id}: {msg_type}")

        except WebSocketDisconnect:
            await server_state.disconnect_client(client_id)
        except Exception as e:
            log.error(f"WebSocket state error for {client_id}: {e}")
            await server_state.disconnect_client(client_id)

    @app.get("/api/projects", response_model=ProjectsResponse)
    async def get_projects(
        paths: Optional[str] = Query(
            None,
            description="Comma-separated list of paths to scan for projects. "
            "If not provided, uses configured workspace paths.",
        ),
    ):
        """
        Discover and return all ato projects in the workspace.

        Projects are discovered by finding ato.yaml files and extracting
        their build targets.
        """
        if paths:
            # Use provided paths
            scan_paths = [Path(p.strip()) for p in paths.split(",")]
        else:
            # Use configured workspace paths
            scan_paths = state["workspace_paths"]

        if not scan_paths:
            return ProjectsResponse(projects=[], total=0)

        projects = discover_projects_in_paths(scan_paths)
        return ProjectsResponse(projects=projects, total=len(projects))

    @app.get("/api/modules", response_model=ModulesResponse)
    async def get_modules(
        project_root: str = Query(
            ...,
            description="Path to the project root to scan for modules",
        ),
        type_filter: Optional[str] = Query(
            None,
            description="Filter by type: 'module', 'interface', or 'component'",
        ),
    ):
        """
        Discover and return all module/interface/component definitions in a project.

        Scans all .ato files in the project (excluding build/ and .ato/ directories)
        and extracts block definitions that can be used as entry points.
        """
        project_path = Path(project_root)

        if not project_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Project not found: {project_root}",
            )

        modules = discover_modules_in_project(project_path)

        # Apply type filter if provided
        if type_filter:
            modules = [m for m in modules if m.type == type_filter]

        # Sort by file then name for consistent ordering
        modules.sort(key=lambda m: (m.file, m.name))

        return ModulesResponse(modules=modules, total=len(modules))

    @app.get("/api/files", response_model=FilesResponse)
    async def get_files(
        project_root: str = Query(
            ...,
            description="Path to the project root to scan for files",
        ),
    ):
        """
        Return a tree of .ato and .py files in the project.

        Scans all files in the project (excluding build/, .ato/, __pycache__,
        .git, etc.) and returns a hierarchical structure.
        """
        project_path = Path(project_root)

        if not project_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Project not found: {project_root}",
            )

        file_tree = core_projects.build_file_tree(project_path, project_path)

        # Count total files (not folders)
        def count_files(nodes: list[FileTreeNode]) -> int:
            count = 0
            for node in nodes:
                if node.type == "file":
                    count += 1
                elif node.children:
                    count += count_files(node.children)
            return count

        total = count_files(file_tree)

        return FilesResponse(files=file_tree, total=total)

    @app.get("/api/dependencies", response_model=DependenciesResponse)
    async def get_dependencies(
        project_root: str = Query(
            ...,
            description="Path to the project root to get dependencies for",
        ),
    ):
        """
        Return the dependencies from a project's ato.yaml file.

        Includes installed version and latest available version info.
        """
        project_path = Path(project_root)

        if not project_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Project not found: {project_root}",
            )

        # Get installed packages for this project
        installed = get_installed_packages_for_project(project_path)

        # Convert to DependencyInfo objects with latest version info
        dependencies: list[DependencyInfo] = []
        for pkg in installed:
            # Parse identifier to get publisher and name
            parts = pkg.identifier.split("/")
            publisher = parts[0] if len(parts) > 1 else "unknown"
            name = parts[-1]

            # Try to get latest version from registry (cached in packages state)
            latest_version = None
            has_update = False

            # Check if we have this package in our cached packages list
            cached_pkg = server_state.packages_by_id.get(pkg.identifier)
            if cached_pkg:
                latest_version = cached_pkg.latest_version
                has_update = registry_model.version_is_newer(
                    pkg.version, latest_version
                )
                # Get repository from cached package info
                repository = cached_pkg.repository
            else:
                repository = None

            dependencies.append(
                DependencyInfo(
                    identifier=pkg.identifier,
                    version=pkg.version,
                    latest_version=latest_version,
                    name=name,
                    publisher=publisher,
                    repository=repository,
                    has_update=has_update,
                )
            )

        return DependenciesResponse(dependencies=dependencies, total=len(dependencies))

    @app.get("/api/summary")
    async def get_summary():
        """
        Return the current build summary, including any active builds.

        Aggregates build summaries from all discovered projects in the workspace.
        Each project's per-target summaries at build/builds/{target}/build_summary.json
        are read and merged.
        """
        all_builds: list[dict] = []
        totals = {"builds": 0, "successful": 0, "failed": 0, "warnings": 0, "errors": 0}

        # First, try the configured summary file (for backwards compatibility)
        summary_path = state["summary_file"]
        if summary_path and summary_path.exists():
            try:
                data = json.loads(summary_path.read_text())
                if "builds" in data:
                    all_builds.extend(data["builds"])
                if "totals" in data:
                    for key in totals:
                        totals[key] += data["totals"].get(key, 0)
            except (json.JSONDecodeError, Exception):
                pass

        # Then, scan all workspace projects for their per-target summaries
        # New structure: {project}/build/builds/{target}/build_summary.json
        workspace_paths = state.get("workspace_paths", [])
        projects = discover_projects_in_paths(workspace_paths)

        for project in projects:
            project_root = Path(project.root)
            builds_dir = project_root / "build" / "builds"

            if not builds_dir.exists():
                continue

            # Scan all target directories for build_summary.json files
            for summary_file in builds_dir.glob("*/build_summary.json"):
                try:
                    data = json.loads(summary_file.read_text())
                    # Each summary file contains a single build
                    build = data

                    # Mark stale building/queued from disk as failed
                    # (only valid if tracked in _active_builds)
                    if build.get("status") in ("building", "queued"):
                        log.debug(
                            f"Marking stale '{build.get('status')}' build "
                            f"as failed: {build.get('name')}"
                        )
                        build["status"] = "failed"
                        build["error"] = "Build was interrupted"

                    if not build.get("project_name"):
                        build["project_name"] = project.name
                    # Update display_name to include project
                    if (
                        build.get("display_name")
                        and project.name not in build["display_name"]
                    ):
                        build["display_name"] = (
                            f"{project.name}:{build['display_name']}"
                        )
                    elif build.get("name") and not build.get("display_name"):
                        build["display_name"] = f"{project.name}:{build['name']}"

                    all_builds.append(build)

                    # Aggregate totals from each build
                    totals["warnings"] += build.get("warnings", 0)
                    totals["errors"] += build.get("errors", 0)
                except (json.JSONDecodeError, Exception) as e:
                    log.warning(f"Failed to read summary from {summary_file}: {e}")

        # Add tracked builds from _active_builds to the response
        # This includes: queued, building, AND recently completed/cancelled
        # This is the SINGLE SOURCE OF TRUTH for build status during a session
        with _build_lock:
            for build_id, build_info in _active_builds.items():
                # Calculate elapsed time based on status:
                # - "building" or completed: time since build actually started
                # - "queued": time waiting in queue
                status = build_info["status"]
                if status in ("building", "success", "failed", "cancelled"):
                    # Use building_started_at for actual build time
                    start_time = build_info.get(
                        "building_started_at", build_info.get("started_at", time.time())
                    )
                else:
                    # Queued: show time waiting
                    start_time = build_info.get("started_at", time.time())
                elapsed = time.time() - start_time

                project_name = Path(build_info["project_root"]).name
                targets = build_info.get("targets", [])
                target_name = (
                    targets[0]
                    if len(targets) == 1
                    else ", ".join(targets)
                    if targets
                    else "default"
                )

                # Create a build entry compatible with the UI
                # Include all fields needed for both queue panel and projects panel
                tracked_build = {
                    # Core identification
                    "build_id": build_id,
                    "name": target_name,
                    "display_name": f"{project_name}:{target_name}",
                    "project_name": project_name,
                    # Status fields
                    "status": status,
                    "elapsed_seconds": elapsed,
                    "started_at": build_info.get("building_started_at")
                    or build_info.get("started_at"),
                    "warnings": build_info.get("warnings", 0),
                    "errors": build_info.get("errors", 0),
                    "return_code": build_info.get("return_code"),
                    # Context for queue panel
                    "project_root": build_info["project_root"],
                    "targets": targets,
                    "entry": build_info.get("entry"),
                    # Real-time stage data
                    "stages": build_info.get("stages", []),
                    # Queue position for queued builds
                    "queue_position": build_info.get("queue_position"),
                    # Error info for failed/cancelled builds
                    "error": build_info.get("error"),
                }

                # Insert tracked builds at the beginning of the list
                all_builds.insert(0, tracked_build)

        # Sort by timestamp/recency if available, most recent first
        # Builds without timestamps go to the end
        def sort_key(build: dict) -> tuple:
            # Active builds (no return_code) first
            is_active = build.get("return_code") is None
            # Then by elapsed time (most recent = highest elapsed for completed)
            elapsed = build.get("elapsed_seconds", 0)
            return (not is_active, -elapsed)

        all_builds.sort(key=sort_key)

        return {"builds": all_builds, "totals": totals}

    @app.post("/api/build", response_model=BuildResponse)
    async def start_build(request: BuildRequest):
        """
        Start a build for the specified project and targets.

        The build runs in the background. Use /api/build/{build_id}/status
        to check progress, or poll /api/summary for results.

        For standalone builds (without ato.yaml), set `standalone=True` and
        provide the `entry` parameter with format "file.ato:Module".
        """
        global _build_counter

        # Validate project path exists
        project_path = Path(request.project_root)
        if not project_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Project path does not exist: {request.project_root}",
            )

        # For standalone builds, verify the entry file exists instead of ato.yaml
        if request.standalone:
            if not request.entry:
                raise HTTPException(
                    status_code=400,
                    detail="Standalone builds require an entry point",
                )
            # Extract file from entry (e.g., "main.ato:App" -> "main.ato")
            entry_file = (
                request.entry.split(":")[0] if ":" in request.entry else request.entry
            )
            entry_path = project_path / entry_file
            if not entry_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Entry file not found: {entry_path}",
                )
        else:
            # Standard build requires ato.yaml
            if not (project_path / "ato.yaml").exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"No ato.yaml found in: {request.project_root}",
                )

        # Check for duplicate builds
        build_key = _make_build_key(
            request.project_root, request.targets, request.entry
        )
        existing_build_id = _is_duplicate_build(build_key)
        if existing_build_id:
            return BuildResponse(
                success=True,
                message="Build already in progress",
                build_id=existing_build_id,
            )

        # Generate build ID
        build_label = request.entry if request.standalone else "project"
        with _build_lock:
            _build_counter += 1
            build_id = f"build-{_build_counter}-{int(time.time())}"

            # Register the build
            _active_builds[build_id] = {
                "status": "queued",
                "project_root": request.project_root,
                "targets": request.targets,
                "entry": request.entry,
                "standalone": request.standalone,
                "frozen": request.frozen,
                "build_key": build_key,
                "return_code": None,
                "error": None,
                "started_at": time.time(),
                "stages": [],
            }

        # Enqueue the build
        _build_queue.enqueue(build_id)

        # Sync to server_state for WebSocket broadcast
        _sync_builds_to_state()

        return BuildResponse(
            success=True,
            message=f"Build queued for {build_label}",
            build_id=build_id,
        )

    @app.get("/api/build/{build_id}/status", response_model=BuildStatusResponse)
    async def get_build_status(build_id: str):
        """Get the status of a specific build."""
        if build_id not in _active_builds:
            raise HTTPException(status_code=404, detail=f"Build not found: {build_id}")

        build = _active_builds[build_id]
        return BuildStatusResponse(
            build_id=build_id,
            status=build["status"],
            project_root=build["project_root"],
            targets=build["targets"],
            return_code=build["return_code"],
            error=build["error"],
        )

    @app.post("/api/build/{build_id}/cancel")
    async def cancel_build_endpoint(build_id: str):
        """Cancel a running build."""
        if build_id not in _active_builds:
            raise HTTPException(status_code=404, detail=f"Build not found: {build_id}")

        success = cancel_build(build_id)
        if success:
            return {"success": True, "message": f"Build {build_id} cancelled"}
        else:
            return {
                "success": False,
                "message": f"Build {build_id} cannot be cancelled (already completed)",
            }

    @app.get("/api/builds/active")
    async def get_active_builds():
        """
        Get all active builds (queued or building) in a display-ready format.

        This endpoint provides all data needed for the queue panel to render
        without any additional processing. Backend is the source of truth.
        """
        builds = []
        with _build_lock:
            for bid, b in _active_builds.items():
                status = b["status"]
                if status not in ("queued", "building"):
                    continue

                # Calculate elapsed time based on status:
                # - "building": time since build actually started
                # - "queued": time waiting in queue
                if status == "building":
                    start_time = b.get(
                        "building_started_at", b.get("started_at", time.time())
                    )
                else:
                    start_time = b.get("started_at", time.time())
                elapsed = time.time() - start_time

                # Format display name
                project_name = Path(b["project_root"]).name
                targets = b.get("targets", [])
                target_name = (
                    targets[0]
                    if len(targets) == 1
                    else ", ".join(targets)
                    if targets
                    else "default"
                )

                builds.append(
                    {
                        # Core fields for the queue panel
                        "build_id": bid,
                        "status": status,
                        "project_root": b["project_root"],
                        "targets": targets,
                        "entry": b.get("entry"),
                        # Display-ready fields
                        "project_name": project_name,
                        "display_name": f"{project_name}:{target_name}",
                        # Timing - prefer building_started_at, else started_at
                        "started_at": b.get("building_started_at")
                        or b.get("started_at"),
                        "elapsed_seconds": elapsed,
                        # Stage data for progress display
                        "stages": b.get("stages", []),
                        # Queue position (1-indexed)
                        "queue_position": b.get("queue_position"),
                        # Error info if any
                        "error": b.get("error"),
                    }
                )

        # Sort: building first, then queued by queue_position
        builds.sort(
            key=lambda x: (
                x["status"] != "building",  # building first
                x.get("queue_position") or 999,  # then by position
            )
        )

        return {"builds": builds}

    @app.get("/api/builds/queue")
    async def get_build_queue_status():
        """Get the current build queue status for debugging."""
        return _build_queue.get_status()

    @app.get("/api/settings/max-concurrent")
    async def get_max_concurrent_setting():
        """Get the max concurrent builds setting."""
        return {
            "use_default": _build_settings["use_default_max_concurrent"],
            "custom_value": _build_settings["custom_max_concurrent"],
            "default_value": _DEFAULT_MAX_CONCURRENT,
            "current_value": _build_queue.get_max_concurrent(),
        }

    class MaxConcurrentRequest(BaseModel):
        use_default: bool = True
        custom_value: int | None = None

    @app.post("/api/settings/max-concurrent")
    async def set_max_concurrent_setting(request: MaxConcurrentRequest):
        """Set the max concurrent builds setting."""
        _build_settings["use_default_max_concurrent"] = request.use_default

        if request.use_default:
            # Use CPU count
            _build_queue.set_max_concurrent(_DEFAULT_MAX_CONCURRENT)
        else:
            # Use custom value
            custom = request.custom_value or _DEFAULT_MAX_CONCURRENT
            _build_settings["custom_max_concurrent"] = custom
            _build_queue.set_max_concurrent(custom)

        return {
            "success": True,
            "use_default": _build_settings["use_default_max_concurrent"],
            "custom_value": _build_settings["custom_max_concurrent"],
            "default_value": _DEFAULT_MAX_CONCURRENT,
            "current_value": _build_queue.get_max_concurrent(),
        }

    @app.get("/api/builds/history")
    async def get_build_history(
        project_root: Optional[str] = Query(None, description="Filter by project root"),
        status: Optional[str] = Query(
            None, description="Filter by status (success, failed, cancelled)"
        ),
        limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    ):
        """
        Get build history from the database.

        Returns historical build records with their stages and outcomes.
        """
        builds = load_recent_builds_from_history(limit=limit)

        # Apply filters
        if project_root:
            builds = [b for b in builds if b["project_root"] == project_root]
        if status:
            builds = [b for b in builds if b["status"] == status]

        return {"builds": builds, "total": len(builds)}

    @app.get("/api/logs/{build_name}/{log_filename}")
    async def get_log_file(build_name: str, log_filename: str):
        """Return a specific log file by filename."""
        try:
            summary_path = state["summary_file"]
            if summary_path is None or not summary_path.exists():
                raise HTTPException(status_code=404, detail="No summary file found")

            summary = json.loads(summary_path.read_text())

            # Find the build and get its log_dir
            log_dir = None
            for build in summary.get("builds", []):
                if (
                    build.get("name") == build_name
                    or build.get("display_name") == build_name
                ):
                    log_dir = build.get("log_dir")
                    break

            if not log_dir:
                raise HTTPException(
                    status_code=404, detail=f"Build not found: {build_name}"
                )

            # Construct the log file path
            log_file = Path(log_dir) / log_filename

            if not log_file.exists():
                raise HTTPException(
                    status_code=404, detail=f"Log file not found: {log_filename}"
                )

            return PlainTextResponse(
                content=log_file.read_text(),
                media_type="text/plain",
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/logs/query")
    async def query_logs(
        # Frontend-compatible parameters
        build_name: Optional[str] = Query(
            None, description="Filter by build/target name (e.g., 'project:target')"
        ),
        project_name: Optional[str] = Query(None, description="Filter by project name"),
        levels: Optional[str] = Query(
            None, description="Comma-separated log levels (DEBUG,INFO,WARNING,ERROR)"
        ),
        search: Optional[str] = Query(None, description="Search in log messages"),
        after_id: Optional[int] = Query(
            None, description="Return logs after this ID (for incremental fetch)"
        ),
        # Backend parameters (also supported)
        build_id: Optional[str] = Query(
            None, description="Filter by build ID (from central database)"
        ),
        project_path: Optional[str] = Query(None, description="Filter by project path"),
        target: Optional[str] = Query(None, description="Filter by target name"),
        stage: Optional[str] = Query(None, description="Filter by build stage"),
        level: Optional[str] = Query(None, description="Filter by single log level"),
        audience: Optional[str] = Query(
            None, description="Filter by audience (user, developer, agent)"
        ),
        limit: int = Query(500, ge=1, le=10000, description="Maximum results"),
        offset: int = Query(0, ge=0, description="Result offset for pagination"),
    ):
        """
        Query logs from the central SQLite database with optional filters.

        Supports both frontend-friendly params (build_name, levels, search)
        and backend params (build_id, project_path, target).
        """
        try:
            # Use central log database
            central_db = get_central_log_db()
            if not central_db.exists():
                return {"logs": [], "total": 0, "max_id": 0, "has_more": False}

            conn = sqlite3.connect(str(central_db), timeout=5.0)
            conn.row_factory = sqlite3.Row

            # Build query with filters
            conditions = []
            params: list = []

            # Handle build_name (format: "project:target" or just "target")
            if build_name:
                if ":" in build_name:
                    # Format: "project:target" - filter by both
                    project_part, target_part = build_name.split(":", 1)
                    conditions.append("builds.target = ?")
                    params.append(target_part)
                    conditions.append("builds.project_path LIKE ?")
                    params.append(f"%/{project_part}")
                else:
                    conditions.append("builds.target = ?")
                    params.append(build_name)

            # Handle project_name - match end of project_path
            if project_name:
                conditions.append("builds.project_path LIKE ?")
                params.append(f"%/{project_name}")

            # Direct filters
            if build_id:
                conditions.append("logs.build_id = ?")
                params.append(build_id)
            if project_path:
                conditions.append("builds.project_path = ?")
                params.append(project_path)
            if target:
                conditions.append("builds.target = ?")
                params.append(target)
            if stage:
                conditions.append("logs.stage = ?")
                params.append(stage)

            # Handle multiple levels (comma-separated)
            if levels:
                level_list = [lv.strip().upper() for lv in levels.split(",")]
                placeholders = ",".join("?" * len(level_list))
                conditions.append(f"logs.level IN ({placeholders})")
                params.extend(level_list)
            elif level:
                conditions.append("logs.level = ?")
                params.append(level.upper())

            if audience:
                conditions.append("logs.audience = ?")
                params.append(audience.lower())

            # Search in message
            if search:
                conditions.append("logs.message LIKE ?")
                params.append(f"%{search}%")

            # Incremental fetch - only logs after a certain ID
            if after_id is not None:
                conditions.append("logs.id > ?")
                params.append(after_id)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            # Query with pagination
            # Use ASC order for incremental (after_id), DESC otherwise
            order = "ASC" if after_id is not None else "DESC"
            query = f"""
                SELECT logs.id, logs.build_id, logs.timestamp, logs.stage,
                       logs.level, logs.audience, logs.message,
                       logs.ato_traceback, logs.python_traceback,
                       builds.project_path, builds.target
                FROM logs
                JOIN builds ON logs.build_id = builds.build_id
                {where_clause}
                ORDER BY logs.id {order}
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            all_logs: list[dict] = []
            max_id = 0
            for row in rows:
                log_id = row["id"]
                if log_id > max_id:
                    max_id = log_id
                all_logs.append(
                    {
                        "id": log_id,
                        "build_id": row["build_id"],
                        "timestamp": row["timestamp"],
                        "stage": row["stage"],
                        "level": row["level"],
                        "audience": row["audience"],
                        "message": row["message"],
                        "ato_traceback": row["ato_traceback"],
                        "python_traceback": row["python_traceback"],
                        "project_path": row["project_path"],
                        "target": row["target"],
                    }
                )

            # Get total count for pagination (without limit/offset)
            count_params = params[:-2] if len(params) >= 2 else []
            count_query = f"""
                SELECT COUNT(*) as total
                FROM logs
                JOIN builds ON logs.build_id = builds.build_id
                {where_clause}
            """
            total = conn.execute(count_query, count_params).fetchone()["total"]
            has_more = len(all_logs) == limit and total > len(all_logs) + offset

            conn.close()
            return {
                "logs": all_logs,
                "total": total,
                "max_id": max_id,
                "has_more": has_more,
            }

        except sqlite3.Error as e:
            log.warning(f"Error reading logs from central database: {e}")
            return {"logs": [], "total": 0, "max_id": 0, "has_more": False}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/logs/counts")
    async def get_log_counts(
        build_name: Optional[str] = Query(
            None, description="Filter by build/target name"
        ),
        project_name: Optional[str] = Query(None, description="Filter by project name"),
        stage: Optional[str] = Query(None, description="Filter by build stage"),
    ):
        """
        Get log counts by level for UI badges.

        Returns counts for each log level (DEBUG, INFO, WARNING, ERROR, ALERT).
        """
        try:
            central_db = get_central_log_db()
            if not central_db.exists():
                return {
                    "counts": {
                        "DEBUG": 0,
                        "INFO": 0,
                        "WARNING": 0,
                        "ERROR": 0,
                        "ALERT": 0,
                    },
                    "total": 0,
                }

            conn = sqlite3.connect(str(central_db), timeout=5.0)
            conn.row_factory = sqlite3.Row

            conditions = []
            params: list = []

            if build_name:
                if ":" in build_name:
                    # Format: "project:target" - filter by both
                    project_part, target_part = build_name.split(":", 1)
                    conditions.append("builds.target = ?")
                    params.append(target_part)
                    conditions.append("builds.project_path LIKE ?")
                    params.append(f"%/{project_part}")
                else:
                    conditions.append("builds.target = ?")
                    params.append(build_name)

            if project_name:
                conditions.append("builds.project_path LIKE ?")
                params.append(f"%/{project_name}")

            if stage:
                conditions.append("logs.stage = ?")
                params.append(stage)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT logs.level, COUNT(*) as count
                FROM logs
                JOIN builds ON logs.build_id = builds.build_id
                {where_clause}
                GROUP BY logs.level
            """

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            counts = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "ALERT": 0}
            total = 0
            for row in rows:
                level = row["level"].upper()
                count = row["count"]
                if level in counts:
                    counts[level] = count
                total += count

            conn.close()
            return {"counts": counts, "total": total}

        except sqlite3.Error as e:
            log.warning(f"Error getting log counts: {e}")
            return {
                "counts": {
                    "DEBUG": 0,
                    "INFO": 0,
                    "WARNING": 0,
                    "ERROR": 0,
                    "ALERT": 0,
                },
                "total": 0,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # --- BOM Endpoints ---

    @app.get("/api/bom")
    async def get_bom(
        project_root: str = Query(
            ...,
            description="Path to the project root (containing ato.yaml)",
        ),
        target: str = Query(
            "default",
            description="Build target name",
        ),
    ):
        """
        Get the BOM (Bill of Materials) for a specific build target.

        Returns the JSON BOM data generated by `ato build`, including:
        - Component details (LCSC, manufacturer, MPN, etc.)
        - Quantities and pricing
        - Usage locations (atopile addresses)
        """
        project_path = Path(project_root)
        if not project_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Project path does not exist: {project_root}",
            )

        if not (project_path / "ato.yaml").exists():
            raise HTTPException(
                status_code=400,
                detail=f"No ato.yaml found in: {project_root}",
            )

        # Build output path: <project>/build/builds/<target>/<target>.bom.json
        bom_path = project_path / "build" / "builds" / target / f"{target}.bom.json"

        if not bom_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"BOM file not found: {bom_path}. "
                f"Run 'ato build' first to generate the BOM.",
            )

        try:
            bom_data = json.loads(bom_path.read_text())
            return bom_data
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid JSON in BOM file: {e}",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/bom/targets")
    async def get_bom_targets(
        project_root: str = Query(
            ...,
            description="Path to the project root (containing ato.yaml)",
        ),
    ):
        """
        List available BOM targets for a project.

        Returns a list of build targets that have generated BOM files.
        """
        project_path = Path(project_root)
        if not project_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Project path does not exist: {project_root}",
            )

        builds_dir = project_path / "build" / "builds"
        if not builds_dir.exists():
            return {"targets": [], "project_root": project_root}

        targets = []
        for target_dir in builds_dir.iterdir():
            if target_dir.is_dir():
                bom_file = target_dir / f"{target_dir.name}.bom.json"
                if bom_file.exists():
                    # Get file modification time
                    mtime = bom_file.stat().st_mtime
                    targets.append(
                        {
                            "name": target_dir.name,
                            "bom_path": str(bom_file),
                            "last_modified": mtime,
                        }
                    )

        # Sort by last modified (most recent first)
        targets.sort(key=lambda t: t["last_modified"], reverse=True)

        return {"targets": targets, "project_root": project_root}

    # --- Variables Endpoints ---

    @app.get("/api/variables")
    async def get_variables(
        project_root: str = Query(
            ...,
            description="Path to the project root (containing ato.yaml)",
        ),
        target: str = Query(
            "default",
            description="Build target name",
        ),
    ):
        """
        Get the variables/parameters for a specific build target.

        Returns the JSON variables data generated by `ato build`, including:
        - Hierarchical module tree with parameters
        - Spec and actual values
        - Units and variable types
        - Source information (user, derived, picked, datasheet)
        """
        project_path = Path(project_root)
        if not project_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Project path does not exist: {project_root}",
            )

        if not (project_path / "ato.yaml").exists():
            raise HTTPException(
                status_code=400,
                detail=f"No ato.yaml found in: {project_root}",
            )

        # Build output path: <project>/build/builds/<target>/<target>.variables.json
        variables_path = (
            project_path / "build" / "builds" / target / f"{target}.variables.json"
        )

        if not variables_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Variables file not found: {variables_path}. "
                f"Run 'ato build' first to generate the variables report.",
            )

        try:
            variables_data = json.loads(variables_path.read_text())
            return variables_data
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Invalid JSON in variables file: {e}",
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/variables/targets")
    async def get_variables_targets(
        project_root: str = Query(
            ...,
            description="Path to the project root (containing ato.yaml)",
        ),
    ):
        """
        List available variables targets for a project.

        Returns a list of build targets that have generated variables files.
        """
        project_path = Path(project_root)
        if not project_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Project path does not exist: {project_root}",
            )

        builds_dir = project_path / "build" / "builds"
        if not builds_dir.exists():
            return {"targets": [], "project_root": project_root}

        targets = []
        for target_dir in builds_dir.iterdir():
            if target_dir.is_dir():
                variables_file = target_dir / f"{target_dir.name}.variables.json"
                if variables_file.exists():
                    # Get file modification time
                    mtime = variables_file.stat().st_mtime
                    targets.append(
                        {
                            "name": target_dir.name,
                            "variables_path": str(variables_file),
                            "last_modified": mtime,
                        }
                    )

        # Sort by last modified (most recent first)
        targets.sort(key=lambda t: t["last_modified"], reverse=True)

        return {"targets": targets, "project_root": project_root}

    # --- Location Resolution Endpoint ---

    @app.get("/api/resolve-location")
    async def resolve_location(
        address: str = Query(
            ...,
            description="Atopile address to resolve (e.g., 'file.ato::Module.field')",
        ),
        project_root: Optional[str] = Query(
            None,
            description="Project root to search from (optional)",
        ),
    ):
        """
        Resolve an atopile address to a file location.

        Address formats supported:
        - `file.ato::Module.field` - Standard address
        - `file.ato::Module.field[0]` - With array index
        - `file.ato::Module.field|Type` - With type annotation

        Returns the file path and line number where the address is defined.
        """
        import re

        # Parse the address
        # Format: file.ato::ModulePath.field[index]|Type
        # or:     path/to/file.ato::ModulePath.field

        # Strip type annotation if present (after |)
        if "|" in address:
            address = address.split("|")[0]

        # Split into file and path parts
        if "::" not in address:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid address format: {address}. Expected 'file.ato::path'",
            )

        file_part, path_part = address.split("::", 1)

        # Find the source file
        source_file = None

        # Try different resolution strategies
        if project_root:
            project_path = Path(project_root)
            # Check if file_part is relative to project
            candidate = project_path / file_part
            if candidate.exists():
                source_file = candidate

            # Check in .ato/modules
            if not source_file:
                modules_dir = project_path / ".ato" / "modules"
                if modules_dir.exists():
                    for ato_file in modules_dir.rglob(file_part):
                        source_file = ato_file
                        break

        # Try as absolute path
        if not source_file:
            candidate = Path(file_part)
            if candidate.exists():
                source_file = candidate

        # Try searching workspace paths
        if not source_file and workspace_paths:
            for ws_path in workspace_paths:
                candidate = ws_path / file_part
                if candidate.exists():
                    source_file = candidate
                    break
                # Also check in subdirectories
                for ato_file in ws_path.rglob(file_part):
                    source_file = ato_file
                    break
                if source_file:
                    break

        if not source_file or not source_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Source file not found: {file_part}",
            )

        # Parse the path to find the specific location
        # path_part is like: Module.submodule.field[0]
        path_segments = []
        current = ""
        for char in path_part:
            if char == ".":
                if current:
                    path_segments.append(current)
                current = ""
            elif char == "[":
                if current:
                    path_segments.append(current)
                current = "["
            elif char == "]":
                current += char
                path_segments.append(current)
                current = ""
            else:
                current += char
        if current:
            path_segments.append(current)

        # Read the source file and find the location
        try:
            content = source_file.read_text()

            # Strategy: Find the definition of each path segment
            # Start with the module/interface definition, then drill down

            line_number = 1
            found = False

            # For the first segment (module name), look for block definition
            if path_segments:
                first_segment = path_segments[0]
                # Look for module/interface/component definition
                block_pattern = re.compile(
                    rf"^\s*(module|interface|component)\s+{re.escape(first_segment)}\s*[:(]",
                    re.MULTILINE,
                )
                match = block_pattern.search(content)
                if match:
                    # Count lines to get line number
                    line_number = content[: match.start()].count("\n") + 1
                    found = True

                    # Now look for nested fields
                    if len(path_segments) > 1:
                        # Find the last field assignment
                        last_field = path_segments[-1]
                        # Remove array index if present
                        field_name = re.sub(r"\[\d+\]$", "", last_field)

                        # Search from the block start
                        block_content = content[match.start() :]
                        # Look for field assignment or declaration
                        field_patterns = [
                            # Assignment: field = ...
                            rf"^\s*{re.escape(field_name)}\s*=",
                            # Declaration with type: field: Type
                            rf"^\s*{re.escape(field_name)}\s*:",
                            # New statement: field = new ...
                            rf"^\s*{re.escape(field_name)}\s*=\s*new\s+",
                        ]

                        for pattern in field_patterns:
                            field_match = re.search(
                                pattern, block_content, re.MULTILINE
                            )
                            if field_match:
                                # Calculate line number
                                line_number = (
                                    content[: match.start()].count("\n")
                                    + block_content[: field_match.start()].count("\n")
                                    + 1
                                )
                                found = True
                                break

            if not found:
                # Fallback: just return line 1
                line_number = 1

            return {
                "file": str(source_file.absolute()),
                "line": line_number,
                "column": 1,
                "address": address,
                "resolved": found,
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error reading source file: {e}",
            )

    # --- Problems Endpoint ---

    @app.get("/api/problems", response_model=ProblemsResponse)
    async def get_problems(
        project_root: Optional[str] = Query(
            None,
            description="Filter to problems from a specific project",
        ),
        build_name: Optional[str] = Query(
            None,
            description="Filter to problems from a specific build target",
        ),
        level: Optional[str] = Query(
            None,
            description="Filter by level: 'error' or 'warning'",
        ),
    ):
        """
        Get all problems (errors and warnings) from recent builds.

        Aggregates problems from all discovered projects in the workspace,
        or from a specific project if project_root is provided.
        """
        all_problems: list[Problem] = []

        # Get workspace paths
        workspace_paths = state.get("workspace_paths", [])
        projects = discover_projects_in_paths(workspace_paths)

        # Filter to specific project if provided
        if project_root:
            projects = [p for p in projects if p.root == project_root]

        for project in projects:
            project_path = Path(project.root)
            project_summary = (
                project_path / "build" / "logs" / "latest" / "summary.json"
            )

            if not project_summary.exists():
                continue

            try:
                summary_data = json.loads(project_summary.read_text())
                builds_data = summary_data.get("builds", [])

                for build in builds_data:
                    # Filter by build_name if provided
                    current_build_name = build.get("name", "")
                    if build_name and current_build_name != build_name:
                        continue

                    # Get log file path
                    log_file_path = build.get("log_file")
                    if not log_file_path:
                        continue

                    log_file = Path(log_file_path)
                    if not log_file.exists():
                        continue

                    # Parse problems from log file
                    build_problems = parse_problems_from_log_file(
                        log_file,
                        build_name=current_build_name,
                        project_name=project.name,
                    )
                    all_problems.extend(build_problems)

            except Exception as e:
                log.warning(f"Failed to read problems from {project_summary}: {e}")
                continue

        # Apply level filter if provided
        if level:
            all_problems = [p for p in all_problems if p.level == level]

        # Count errors and warnings
        error_count = sum(1 for p in all_problems if p.level == "error")
        warning_count = sum(1 for p in all_problems if p.level == "warning")

        return ProblemsResponse(
            problems=all_problems,
            total=len(all_problems),
            error_count=error_count,
            warning_count=warning_count,
        )

    @app.get("/api/stdlib", response_model=StdLibResponse)
    async def get_stdlib(
        type_filter: Optional[str] = Query(
            None,
            description="Filter by item type: interface, module, trait, component",
        ),
        search: Optional[str] = Query(
            None,
            description="Search query to filter items by name or description",
        ),
        refresh: bool = Query(
            False,
            description="Force refresh the library cache",
        ),
        max_depth: Optional[int] = Query(
            None,
            description="Maximum depth for nested children. 0=none, 1=one level, "
            "2=default (two levels). Changing this forces a cache refresh.",
            ge=0,
            le=5,
        ),
    ):
        """
        Get standard library items (modules, interfaces, traits).

        Returns structured data about the faebryk standard library
        for display in the UI.
        """
        items = get_standard_library(force_refresh=refresh, max_depth=max_depth)

        # Apply type filter
        if type_filter:
            try:
                filter_type = StdLibItemType(type_filter.lower())
                items = [item for item in items if item.type == filter_type]
            except ValueError:
                pass  # Invalid filter, return all

        # Apply search filter
        if search:
            search_lower = search.lower()
            items = [
                item
                for item in items
                if search_lower in item.name.lower()
                or search_lower in item.description.lower()
            ]

        return StdLibResponse(items=items, total=len(items))

    @app.get("/api/stdlib/{item_id}", response_model=StdLibItem)
    async def get_stdlib_item(item_id: str):
        """
        Get a specific standard library item by ID.
        """
        items = get_standard_library()
        for item in items:
            if item.id == item_id:
                return item

        raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")

    # --- Package Management Endpoints ---

    @app.get("/api/registry/search", response_model=RegistrySearchResponse)
    async def search_registry(
        query: str = Query(
            "",
            description="Search query. Empty returns popular packages.",
        ),
        paths: Optional[str] = Query(
            None,
            description="Comma-separated list of paths to check installed packages.",
        ),
    ):
        """
        Search the package registry for available packages.

        Returns packages from the registry with their installation status
        based on the local workspace.
        """
        # Get packages from registry
        registry_packages = search_registry_packages(query)

        # Get installed packages to merge installation status
        if paths:
            scan_paths = [Path(p.strip()) for p in paths.split(",")]
        else:
            scan_paths = state["workspace_paths"]

        if scan_paths:
            installed_map = get_all_installed_packages(scan_paths)

            # Merge installation status
            for pkg in registry_packages:
                if pkg.identifier in installed_map:
                    installed = installed_map[pkg.identifier]
                    pkg.installed = True
                    pkg.installed_in = installed.installed_in
                    pkg.version = installed.version

        return RegistrySearchResponse(
            packages=registry_packages,
            total=len(registry_packages),
            query=query,
        )

    @app.get("/api/packages/summary", response_model=PackagesSummaryResponse)
    async def get_packages_summary(
        paths: Optional[str] = Query(
            None,
            description="Comma-separated list of paths to scan for projects. "
            "If not provided, uses configured workspace paths.",
        ),
    ):
        """
        Get unified packages summary for the packages panel.

        This is the single endpoint that the frontend should call for the packages
        panel. It merges installed packages with registry metadata and provides
        a pre-computed display-ready response.

        Benefits:
        - Single API call instead of two racing calls
        - Registry errors are visible via registry_status
        - has_update is pre-computed
        - All merge logic happens on the backend

        Returns packages sorted by: installed first, then alphabetically.
        """
        # Parse paths
        if paths:
            scan_paths = [Path(p.strip()) for p in paths.split(",")]
        else:
            scan_paths = state["workspace_paths"]

        # 1. Get installed packages (always works - local files)
        packages_map: dict[str, PackageSummaryItem] = {}
        installed_count = 0

        if scan_paths:
            installed = get_all_installed_packages(scan_paths)
            installed_count = len(installed)

            for identifier, pkg in installed.items():
                packages_map[identifier] = PackageSummaryItem(
                    identifier=pkg.identifier,
                    name=pkg.name,
                    publisher=pkg.publisher,
                    installed=True,
                    version=pkg.version,
                    installed_in=pkg.installed_in,
                )

        # 2. Try registry (with error handling)
        # Use get_all_registry_packages() which queries multiple terms to get all pkgs
        registry_status = RegistryStatus(available=True, error=None)
        registry_error: str | None = None

        try:
            registry_packages = get_all_registry_packages()
            log.info(
                f"[packages/summary] Registry returned {len(registry_packages)} pkgs, "
                f"installed: {installed_count}"
            )

            # Merge registry data into packages_map
            for reg_pkg in registry_packages:
                if reg_pkg.identifier in packages_map:
                    # Update installed package with registry metadata
                    existing = packages_map[reg_pkg.identifier]
                    packages_map[reg_pkg.identifier] = PackageSummaryItem(
                        identifier=existing.identifier,
                        name=existing.name,
                        publisher=existing.publisher,
                        installed=True,
                        version=existing.version,
                        installed_in=existing.installed_in,
                        latest_version=reg_pkg.latest_version,
                        has_update=_version_is_newer(
                            existing.version, reg_pkg.latest_version
                        ),
                        summary=reg_pkg.summary,
                        description=reg_pkg.description or reg_pkg.summary,
                        homepage=reg_pkg.homepage,
                        repository=reg_pkg.repository,
                        license=reg_pkg.license,
                        downloads=reg_pkg.downloads,
                        version_count=reg_pkg.version_count,
                        keywords=reg_pkg.keywords or [],
                    )
                else:
                    # Add uninstalled registry package
                    packages_map[reg_pkg.identifier] = PackageSummaryItem(
                        identifier=reg_pkg.identifier,
                        name=reg_pkg.name,
                        publisher=reg_pkg.publisher,
                        installed=False,
                        latest_version=reg_pkg.latest_version,
                        has_update=False,
                        summary=reg_pkg.summary,
                        description=reg_pkg.description or reg_pkg.summary,
                        homepage=reg_pkg.homepage,
                        repository=reg_pkg.repository,
                        license=reg_pkg.license,
                        downloads=reg_pkg.downloads,
                        version_count=reg_pkg.version_count,
                        keywords=reg_pkg.keywords or [],
                    )

        except Exception as e:
            registry_error = str(e)
            registry_status = RegistryStatus(
                available=False,
                error=f"Registry unavailable: {registry_error}",
            )
            log.warning(f"Registry fetch failed for packages summary: {e}")

        # 3. Sort packages: installed first, then alphabetically
        packages_list = sorted(
            packages_map.values(),
            key=lambda p: (not p.installed, p.identifier.lower()),
        )

        log.info(
            f"[packages/summary] Returning {len(packages_list)} total packages "
            f"(installed: {installed_count})"
        )
        return PackagesSummaryResponse(
            packages=packages_list,
            total=len(packages_list),
            installed_count=installed_count,
            registry_status=registry_status,
        )

    @app.get("/api/packages", response_model=PackagesResponse)
    async def get_packages(
        paths: Optional[str] = Query(
            None,
            description="Comma-separated list of paths to scan for projects. "
            "If not provided, uses configured workspace paths.",
        ),
        project_root: Optional[str] = Query(
            None,
            description="Filter to packages installed in a specific project.",
        ),
        include_registry: bool = Query(
            True,
            description="Include latest_version and metadata from registry.",
        ),
    ):
        """
        Get installed packages across all projects in the workspace.

        Returns packages with their installation status and which projects
        they are installed in. If include_registry is True, also fetches
        latest_version and metadata from the package registry.
        """
        if paths:
            scan_paths = [Path(p.strip()) for p in paths.split(",")]
        else:
            scan_paths = state["workspace_paths"]

        if not scan_paths:
            return PackagesResponse(packages=[], total=0)

        packages_map = get_all_installed_packages(scan_paths)

        # Optionally enrich with registry data
        if include_registry:
            packages_map = enrich_packages_with_registry(packages_map)

        # Filter by project if specified
        if project_root:
            packages_list = [
                pkg for pkg in packages_map.values() if project_root in pkg.installed_in
            ]
        else:
            packages_list = list(packages_map.values())

        # Sort by identifier
        packages_list.sort(key=lambda p: p.identifier.lower())

        return PackagesResponse(packages=packages_list, total=len(packages_list))

    # NOTE: /details endpoint MUST come before /{package_id:path} to avoid
    # the path parameter consuming the /details suffix
    @app.get("/api/packages/{package_id:path}/details", response_model=PackageDetails)
    async def get_package_details(
        package_id: str,
        paths: Optional[str] = Query(None),
    ):
        """
        Get detailed information about a package from the registry.

        Returns:
        - Stats (downloads, etc.)
        - All available versions
        - Installation status

        package_id should be in format "publisher/name" e.g., "atopile/bosch-bme280"
        """
        # Get details from registry
        details = get_package_details_from_registry(package_id)

        if not details:
            raise HTTPException(
                status_code=404,
                detail=f"Package not found in registry: {package_id}",
            )

        # Check installation status
        if paths:
            scan_paths = [Path(p.strip()) for p in paths.split(",")]
        else:
            scan_paths = state["workspace_paths"]

        if scan_paths:
            packages_map = get_all_installed_packages(scan_paths)
            if package_id in packages_map:
                installed = packages_map[package_id]
                details.installed = True
                details.installed_version = installed.version
                details.installed_in = installed.installed_in

        return details

    @app.get("/api/packages/{package_id:path}", response_model=PackageInfo)
    async def get_package(
        package_id: str,
        paths: Optional[str] = Query(None),
    ):
        """
        Get information about a specific package.

        package_id should be in format "publisher/name" e.g., "atopile/bosch-bme280"
        """
        if paths:
            scan_paths = [Path(p.strip()) for p in paths.split(",")]
        else:
            scan_paths = state["workspace_paths"]

        packages_map = get_all_installed_packages(scan_paths)

        if package_id in packages_map:
            return packages_map[package_id]

        # Package not installed - return basic info
        parts = package_id.split("/")
        if len(parts) == 2:
            publisher, name = parts
        else:
            publisher = "unknown"
            name = package_id

        return PackageInfo(
            identifier=package_id,
            name=name,
            publisher=publisher,
            installed=False,
        )

    @app.post("/api/packages/install", response_model=PackageActionResponse)
    async def install_package(
        request: PackageActionRequest,
        background_tasks: BackgroundTasks,
    ):
        """
        Install a package into a project.

        Runs `ato add <package>` in the background.
        """
        global _package_op_counter

        project_path = Path(request.project_root)
        if not project_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Project path does not exist: {request.project_root}",
            )

        if not (project_path / "ato.yaml").exists():
            raise HTTPException(
                status_code=400,
                detail=f"No ato.yaml found in: {request.project_root}",
            )

        # Generate operation ID
        with _package_op_lock:
            _package_op_counter += 1
            op_id = f"pkg-install-{_package_op_counter}-{int(time.time())}"

            _active_package_ops[op_id] = {
                "action": "install",
                "status": "running",
                "package": request.package_identifier,
                "project_root": request.project_root,
                "error": None,
            }

        # Build command
        cmd = ["ato", "add", request.package_identifier]
        if request.version:
            cmd.append(f"@{request.version}")

        # Run in background
        def run_install():
            try:
                result = subprocess.run(
                    cmd,
                    cwd=request.project_root,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                with _package_op_lock:
                    if result.returncode == 0:
                        _active_package_ops[op_id]["status"] = "success"
                    else:
                        _active_package_ops[op_id]["status"] = "failed"
                        _active_package_ops[op_id]["error"] = result.stderr[:500]
            except Exception as e:
                with _package_op_lock:
                    _active_package_ops[op_id]["status"] = "failed"
                    _active_package_ops[op_id]["error"] = str(e)

        background_tasks.add_task(run_install)

        return PackageActionResponse(
            success=True,
            message=f"Installing {request.package_identifier}...",
            action="install",
        )

    @app.post("/api/packages/remove", response_model=PackageActionResponse)
    async def remove_package(
        request: PackageActionRequest,
        background_tasks: BackgroundTasks,
    ):
        """
        Remove a package from a project.

        Runs `ato remove <package>` in the background.
        """
        global _package_op_counter

        project_path = Path(request.project_root)
        if not project_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Project path does not exist: {request.project_root}",
            )

        # Generate operation ID
        with _package_op_lock:
            _package_op_counter += 1
            op_id = f"pkg-remove-{_package_op_counter}-{int(time.time())}"

            _active_package_ops[op_id] = {
                "action": "remove",
                "status": "running",
                "package": request.package_identifier,
                "project_root": request.project_root,
                "error": None,
            }

        cmd = ["ato", "remove", request.package_identifier]

        def run_remove():
            try:
                result = subprocess.run(
                    cmd,
                    cwd=request.project_root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                with _package_op_lock:
                    if result.returncode == 0:
                        _active_package_ops[op_id]["status"] = "success"
                    else:
                        _active_package_ops[op_id]["status"] = "failed"
                        _active_package_ops[op_id]["error"] = result.stderr[:500]
            except Exception as e:
                with _package_op_lock:
                    _active_package_ops[op_id]["status"] = "failed"
                    _active_package_ops[op_id]["error"] = str(e)

        background_tasks.add_task(run_remove)

        return PackageActionResponse(
            success=True,
            message=f"Removing {request.package_identifier}...",
            action="remove",
        )

    # --- Project Creation Endpoint ---

    class CreateProjectRequest(BaseModel):
        """Request to create a new project"""

        parent_directory: str  # Directory to create project in
        name: str | None = None  # Optional name (auto-generated if not provided)

    class CreateProjectResponse(BaseModel):
        """Response from project creation"""

        success: bool
        message: str
        project_root: str | None = None
        project_name: str | None = None

    @app.post("/api/project/create", response_model=CreateProjectResponse)
    async def create_project(request: CreateProjectRequest):
        """
        Create a new minimal atopile project.

        Creates a project with:
        - ato.yaml (build configuration)
        - main.ato (entry point module)
        - layouts/ directory

        The project can be renamed and customized after creation.
        """
        parent_dir = Path(request.parent_directory)
        project_dir: Path | None = None
        try:
            project_dir, project_name = core_projects.create_project(
                parent_dir, request.name
            )
            log.info(f"Created new project: {project_dir}")

            return CreateProjectResponse(
                success=True,
                message=f"Created project '{project_name}'",
                project_root=str(project_dir),
                project_name=project_name,
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        except Exception as e:
            # Clean up if creation failed
            if project_dir and project_dir.exists():
                import shutil

                shutil.rmtree(project_dir, ignore_errors=True)

            log.error(f"Failed to create project: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create project: {e}",
            )

    class RenameProjectRequest(BaseModel):
        """Request to rename a project"""

        project_root: str
        new_name: str

    class RenameProjectResponse(BaseModel):
        """Response from project rename"""

        success: bool
        message: str
        old_root: str
        new_root: str | None = None

    @app.post("/api/project/rename", response_model=RenameProjectResponse)
    async def rename_project(request: RenameProjectRequest):
        """
        Rename a project directory.

        Moves the project to a new directory with the given name.
        """
        import shutil

        project_path = Path(request.project_root)
        if not project_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Project does not exist: {request.project_root}",
            )

        # Validate new name
        if not request.new_name or "/" in request.new_name or "\\" in request.new_name:
            raise HTTPException(
                status_code=400,
                detail="Invalid project name",
            )

        new_path = project_path.parent / request.new_name

        if new_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Directory already exists: {new_path}",
            )

        try:
            shutil.move(str(project_path), str(new_path))

            # Update main.ato docstring if it has the old name
            main_ato = new_path / "main.ato"
            if main_ato.exists():
                content = main_ato.read_text()
                old_name = project_path.name
                if f'"""{old_name}' in content:
                    content = content.replace(
                        f'"""{old_name}', f'"""{request.new_name}'
                    )
                    main_ato.write_text(content)

            log.info(f"Renamed project: {project_path} -> {new_path}")

            return RenameProjectResponse(
                success=True,
                message=f"Renamed to '{request.new_name}'",
                old_root=str(project_path),
                new_root=str(new_path),
            )

        except Exception as e:
            log.error(f"Failed to rename project: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to rename project: {e}",
            )

    return app


def find_free_port() -> int:
    """Find a free port to use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class DashboardServer:
    """Manages the dashboard server lifecycle."""

    def __init__(
        self,
        summary_file: Path,
        logs_base: Path,
        port: Optional[int] = None,
        workspace_paths: Optional[list[Path]] = None,
    ):
        self.summary_file = summary_file
        self.logs_base = logs_base
        self.port = port or find_free_port()
        self.workspace_paths = workspace_paths or []
        self.app = create_app(summary_file, logs_base, self.workspace_paths)
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        """Get the dashboard URL."""
        return f"http://localhost:{self.port}"

    def start(self) -> None:
        """Start the server in a background thread."""
        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
        )
        self._server = uvicorn.Server(config)

        def run():
            self._server.run()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

        # Wait for server to be ready
        for _ in range(50):  # Wait up to 5 seconds
            if self._server.started:
                break
            time.sleep(0.1)

    def shutdown(self) -> None:
        """Shutdown the server."""
        if self._server:
            self._server.should_exit = True
            if self._thread:
                self._thread.join(timeout=2.0)


def start_dashboard_server(
    summary_file: Path,
    logs_base: Optional[Path] = None,
    port: Optional[int] = None,
    workspace_paths: Optional[list[Path]] = None,
) -> tuple[DashboardServer, str]:
    """
    Start the dashboard server.

    Args:
        summary_file: Path to the summary.json file
        logs_base: Base directory for logs (defaults to summary_file's parent)
        port: Port to use (defaults to a free port)
        workspace_paths: List of workspace paths to scan for projects

    Returns:
        Tuple of (DashboardServer, url)
    """
    if logs_base is None:
        logs_base = summary_file.parent

    server = DashboardServer(summary_file, logs_base, port, workspace_paths)
    server.start()
    return server, server.url
