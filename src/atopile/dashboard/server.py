"""
FastAPI server for the build dashboard API.

Provides API endpoints for build data. The React frontend is served
directly by VS Code webview for better IDE integration.
"""

import asyncio
import hashlib
import json
import logging
import queue
import select
import socket
import sqlite3
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

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

from atopile.dashboard.stdlib import (
    StdLibItem,
    StdLibItemType,
    StdLibResponse,
    get_standard_library,
)

# Registry cache
_registry_cache: dict[str, "PackageInfo"] = {}
_registry_cache_time: float = 0
_REGISTRY_CACHE_TTL = 300  # 5 minutes

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
                await self.send_filtered_logs(client)

        elif action == "unsubscribe":
            client.subscribed_channels.discard(channel)

    async def send_filtered_logs(self, client: ClientSubscription):
        """Query SQLite with client's filters and send results."""
        if not self._db_path or not self._db_path.exists():
            return

        filters = client.log_filters
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Build WHERE clause based on filters
            conditions = []
            params = []

            if filters.get("build_name"):
                conditions.append("build_name = ?")
                params.append(filters["build_name"])

            if filters.get("project_name"):
                conditions.append("build_name LIKE ?")
                params.append(f"%{filters['project_name']}%")

            if filters.get("levels"):
                placeholders = ",".join("?" * len(filters["levels"]))
                conditions.append(f"level IN ({placeholders})")
                params.extend(filters["levels"])

            if filters.get("search"):
                conditions.append("message LIKE ?")
                params.append(f"%{filters['search']}%")

            if filters.get("after_id"):
                conditions.append("id > ?")
                params.append(filters["after_id"])

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            limit = filters.get("limit", 100)

            query = f"""
                SELECT id, timestamp, level, message, source, build_name
                FROM logs
                WHERE {where_clause}
                ORDER BY id DESC
                LIMIT ?
            """
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            logs = [dict(row) for row in reversed(rows)]  # Reverse to chronological

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

    def log_matches_filter(self, log_entry: dict, filters: dict) -> bool:
        """Check if a log entry matches client's filter criteria."""
        if filters.get("levels") and log_entry.get("level") not in filters["levels"]:
            return False
        if filters.get("build_name"):
            if log_entry.get("build_name") != filters["build_name"]:
                return False
        if filters.get("project_name"):
            if filters["project_name"] not in log_entry.get("build_name", ""):
                return False
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
        loop = getattr(self, '_main_loop', None)
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
        loop = getattr(self, '_main_loop', None)
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
    from atopile.compiler.parse import parse_file
    from atopile.compiler.parser.AtoParser import AtoParser

    modules: list[ModuleDefinition] = []

    try:
        tree = parse_file(ato_file)
    except Exception as e:
        log.warning(f"Failed to parse {ato_file}: {e}")
        return modules

    # Get relative path from project root
    try:
        rel_path = ato_file.relative_to(project_root)
    except ValueError:
        rel_path = ato_file.name

    def extract_blockdefs(ctx) -> None:
        """Recursively extract block definitions from parse tree."""
        if ctx is None:
            return

        # Check if this is a blockdef context
        if isinstance(ctx, AtoParser.BlockdefContext):
            try:
                # Get block type (module/interface/component)
                blocktype_ctx = ctx.blocktype()
                if blocktype_ctx:
                    if blocktype_ctx.MODULE():
                        block_type = "module"
                    elif blocktype_ctx.INTERFACE():
                        block_type = "interface"
                    elif blocktype_ctx.COMPONENT():
                        block_type = "component"
                    else:
                        block_type = "unknown"
                else:
                    block_type = "unknown"

                # Get the name from type_reference
                type_ref_ctx = ctx.type_reference()
                if type_ref_ctx:
                    # type_reference returns a name context directly
                    name_ctx = type_ref_ctx.name()
                    if name_ctx:
                        name = name_ctx.getText()
                    else:
                        name = type_ref_ctx.getText()
                else:
                    name = "Unknown"

                # Get super type if present (from blockdef_super)
                super_type = None
                super_ctx = ctx.blockdef_super()
                if super_ctx:
                    super_type_ref = super_ctx.type_reference()
                    if super_type_ref:
                        super_type = super_type_ref.getText()

                # Get line number
                line = ctx.start.line if ctx.start else None

                # Create entry point string
                entry = f"{rel_path}:{name}"

                modules.append(
                    ModuleDefinition(
                        name=name,
                        type=block_type,
                        file=str(rel_path),
                        entry=entry,
                        line=line,
                        super_type=super_type,
                    )
                )
            except Exception as e:
                log.debug(f"Failed to extract blockdef: {e}")

        # Recurse into children
        if hasattr(ctx, "children") and ctx.children:
            for child in ctx.children:
                extract_blockdefs(child)

    # Start extraction from the root
    extract_blockdefs(tree)

    return modules


def discover_modules_in_project(project_root: Path) -> list[ModuleDefinition]:
    """
    Discover all module definitions in a project by scanning .ato files.
    """
    all_modules: list[ModuleDefinition] = []

    # Find all .ato files in the project (excluding build directory)
    for ato_file in project_root.rglob("*.ato"):
        # Skip files in build directories
        if "build" in ato_file.parts:
            continue
        # Skip files in .ato directory (dependencies)
        if ".ato" in ato_file.parts:
            continue

        modules = extract_modules_from_file(ato_file, project_root)
        all_modules.extend(modules)

    return all_modules


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


def search_registry_packages(query: str) -> list[PackageInfo]:
    """
    Search the package registry for packages matching the query.

    Uses the PackagesAPIClient to query the registry API.
    Results are cached for 5 minutes.
    """
    global _registry_cache, _registry_cache_time

    cache_key = f"search:{query}"
    now = time.time()

    # Check cache
    if (
        cache_key in _registry_cache
        and (now - _registry_cache_time) < _REGISTRY_CACHE_TTL
    ):
        return _registry_cache[cache_key]

    try:
        from faebryk.libs.backend.packages.api import PackagesAPIClient

        api = PackagesAPIClient()
        result = api.query_packages(query)

        packages: list[PackageInfo] = []
        for pkg in result.packages:
            # Parse identifier to get publisher and name
            parts = pkg.identifier.split("/")
            if len(parts) == 2:
                publisher, name = parts
            else:
                publisher = "unknown"
                name = pkg.identifier

            packages.append(
                PackageInfo(
                    identifier=pkg.identifier,
                    name=name,
                    publisher=publisher,
                    latest_version=pkg.version,
                    summary=pkg.summary,
                    description=pkg.summary,  # Registry only has summary
                    homepage=pkg.homepage,
                    repository=pkg.repository,
                    installed=False,
                    installed_in=[],
                )
            )

        # Update cache
        _registry_cache[cache_key] = packages
        _registry_cache_time = now

        return packages

    except Exception as e:
        log.warning(f"Failed to search registry: {e}")
        return []


def get_package_details_from_registry(identifier: str) -> PackageDetails | None:
    """
    Get detailed package information from the registry.

    Fetches:
    - Full package info with stats (downloads)
    - List of releases (versions)
    """
    try:
        from faebryk.libs.backend.packages.api import PackagesAPIClient

        api = PackagesAPIClient()

        # Get full package info (includes stats)
        pkg_response = api.get_package(identifier)
        pkg_info = pkg_response.info

        # Get all releases
        releases_response = api._get(f"/v1/package/{identifier}/releases")
        releases_data = releases_response.json()
        releases = releases_data.get("releases", [])

        # Parse identifier
        parts = identifier.split("/")
        if len(parts) == 2:
            publisher, name = parts
        else:
            publisher = "unknown"
            name = identifier

        # Build version list
        versions = []
        for rel in releases:
            released_at = rel.get("released_at")
            if isinstance(released_at, str):
                # Keep as is
                pass
            elif hasattr(released_at, "isoformat"):
                released_at = released_at.isoformat()
            else:
                released_at = None

            versions.append(
                PackageVersion(
                    version=rel.get("version", "unknown"),
                    released_at=released_at,
                    requires_atopile=rel.get("requires_atopile"),
                    size=rel.get("size"),
                )
            )

        # Sort versions by release date (newest first)
        versions.sort(key=lambda v: v.released_at or "", reverse=True)

        # Extract stats
        stats = pkg_info.stats if hasattr(pkg_info, "stats") else None

        return PackageDetails(
            identifier=identifier,
            name=name,
            publisher=publisher,
            version=pkg_info.version,
            summary=pkg_info.summary,
            description=pkg_info.summary,  # API only has summary
            homepage=pkg_info.homepage,
            repository=pkg_info.repository,
            license=pkg_info.license if hasattr(pkg_info, "license") else None,
            downloads=stats.total_downloads if stats else None,
            downloads_this_week=stats.this_week_downloads if stats else None,
            downloads_this_month=stats.this_month_downloads if stats else None,
            versions=versions,
            version_count=len(versions),
        )

    except Exception as e:
        log.warning(f"Failed to get package details for {identifier}: {e}")
        return None


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
    ato_yaml = project_root / "ato.yaml"
    if not ato_yaml.exists():
        return []

    try:
        with open(ato_yaml, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            return []

        packages: list[InstalledPackage] = []
        dependencies = data.get("dependencies", [])

        # Handle list format (current format)
        if isinstance(dependencies, list):
            for dep in dependencies:
                if isinstance(dep, dict):
                    identifier = dep.get("identifier", "")
                    version = dep.get("release", dep.get("version", "unknown"))
                    if identifier:
                        packages.append(
                            InstalledPackage(
                                identifier=identifier,
                                version=version,
                                project_root=str(project_root),
                            )
                        )

        # Handle dict format (legacy format)
        elif isinstance(dependencies, dict):
            for dep_id, dep_info in dependencies.items():
                if isinstance(dep_info, str):
                    # Simple format: "package-id": "version"
                    version = dep_info
                elif isinstance(dep_info, dict):
                    # Dict format: "package-id": {"version": "x.y.z", ...}
                    version = dep_info.get("version", "unknown")
                else:
                    continue

                packages.append(
                    InstalledPackage(
                        identifier=dep_id,
                        version=version,
                        project_root=str(project_root),
                    )
                )

        return packages

    except Exception as e:
        log.warning(f"Failed to read packages from {ato_yaml}: {e}")
        return []


def get_all_installed_packages(paths: list[Path]) -> dict[str, PackageInfo]:
    """
    Get all installed packages across all projects in the given paths.

    Returns a dict of package_identifier -> PackageInfo, with installed_in
    tracking which projects have each package.
    """
    packages_map: dict[str, PackageInfo] = {}

    # Discover all projects
    projects = discover_projects_in_paths(paths)

    for project in projects:
        project_root = Path(project.root)
        installed = get_installed_packages_for_project(project_root)

        for pkg in installed:
            if pkg.identifier not in packages_map:
                # Parse identifier to get publisher and name
                parts = pkg.identifier.split("/")
                if len(parts) == 2:
                    publisher, name = parts
                else:
                    publisher = "unknown"
                    name = pkg.identifier

                packages_map[pkg.identifier] = PackageInfo(
                    identifier=pkg.identifier,
                    name=name,
                    publisher=publisher,
                    version=pkg.version,
                    installed=True,
                    installed_in=[project.root],
                )
            else:
                # Package already seen, add this project to installed_in
                if project.root not in packages_map[pkg.identifier].installed_in:
                    packages_map[pkg.identifier].installed_in.append(project.root)

    return packages_map


def enrich_packages_with_registry(
    packages: dict[str, PackageInfo],
) -> dict[str, PackageInfo]:
    """
    Enrich installed packages with metadata from the registry.

    Fetches latest_version, summary, homepage, etc. from the registry
    for each installed package.
    """
    if not packages:
        return packages

    # Try to get registry data for all identifiers
    # First try batch via search, then individual lookups for missing
    registry_data = search_registry_packages("")

    # Build lookup map
    registry_map: dict[str, PackageInfo] = {
        pkg.identifier: pkg for pkg in registry_data
    }

    # Enrich each installed package
    enriched: dict[str, PackageInfo] = {}
    for identifier, pkg in packages.items():
        if identifier in registry_map:
            reg = registry_map[identifier]
            enriched[identifier] = PackageInfo(
                identifier=pkg.identifier,
                name=pkg.name,
                publisher=pkg.publisher,
                version=pkg.version,
                latest_version=reg.latest_version,
                description=reg.description,
                summary=reg.summary,
                homepage=reg.homepage,
                repository=reg.repository,
                license=reg.license,
                installed=True,
                installed_in=pkg.installed_in,
            )
        else:
            # Not found in registry, keep original
            enriched[identifier] = pkg

    return enriched


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
            if (
                build.get("build_key") == build_key
                and build["status"] in ("queued", "building")
            ):
                return build_id
    return None


class BuildQueue:
    """
    Manages build execution with concurrency limiting.

    Queues build requests and processes them respecting a maximum
    concurrent build limit.
    """

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_BUILDS):
        self._queue: queue.Queue[str] = queue.Queue()
        self._active: set[str] = set()
        self._max_concurrent = max_concurrent
        self._lock = threading.Lock()
        self._worker_thread: threading.Thread | None = None
        self._running = False

    def enqueue(self, build_id: str) -> bool:
        """
        Add a build to the queue.

        Returns True if enqueued, False if already in queue/active.
        """
        with self._lock:
            if build_id in self._active:
                log.debug(f"BuildQueue: {build_id} already active, not enqueueing")
                return False
            self._queue.put(build_id)
            log.debug(
                f"BuildQueue: Enqueued {build_id} "
                f"(queue_size={self._queue.qsize()}, active={len(self._active)})"
            )
            self._start_worker_if_needed()
            return True

    def _start_worker_if_needed(self):
        """Start the worker thread if not already running."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._process_queue, daemon=True
            )
            self._worker_thread.start()
            log.debug("BuildQueue: Started worker thread")

    def _process_queue(self):
        """Process builds from the queue, respecting concurrency limits."""
        log.debug("BuildQueue: Worker thread starting")
        while self._running:
            # Wait for a slot to become available
            while len(self._active) >= self._max_concurrent:
                time.sleep(0.1)
                if not self._running:
                    return

            try:
                build_id = self._queue.get(timeout=1.0)
            except queue.Empty:
                # Check if we should shut down
                if self._queue.empty() and not self._active:
                    log.debug("BuildQueue: Worker thread shutting down (idle)")
                    self._running = False
                    return
                continue

            # Check if build was cancelled while queued
            with _build_lock:
                if build_id not in _active_builds:
                    log.debug(f"BuildQueue: {build_id} no longer exists, skipping")
                    continue
                if _active_builds[build_id].get("status") == "cancelled":
                    log.debug(f"BuildQueue: {build_id} was cancelled, skipping")
                    continue
                build_info = _active_builds[build_id].copy()

            with self._lock:
                self._active.add(build_id)
                log.info(
                    f"BuildQueue: Starting {build_id} "
                    f"(active={len(self._active)}/{self._max_concurrent})"
                )

            # Run the build in a separate thread to allow parallel execution
            def run_build(bid: str, info: dict):
                try:
                    _run_build_subprocess(
                        bid,
                        info["project_root"],
                        info["targets"],
                        info.get("frozen", False),
                        info.get("entry"),
                        info.get("standalone", False),
                    )
                finally:
                    with self._lock:
                        self._active.discard(bid)
                        log.debug(
                            f"BuildQueue: Finished {bid} "
                            f"(active={len(self._active)}, queue={self._queue.qsize()})"
                        )

            build_thread = threading.Thread(
                target=run_build,
                args=(build_id, build_info),
                daemon=True,
            )
            build_thread.start()

        log.debug("BuildQueue: Worker thread exiting")

    def cancel(self, build_id: str) -> bool:
        """
        Remove a build from the queue if it hasn't started yet.

        Returns True if the build was in the queue and removed.
        """
        # Note: We can't remove from queue.Queue directly, but we mark
        # the build as cancelled in _active_builds and skip it in _process_queue
        with self._lock:
            return build_id in self._active or not self._queue.empty()

    def stop(self) -> None:
        """Stop the worker thread and wait for it to finish."""
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        self._worker_thread = None

    def clear(self) -> None:
        """Clear the queue and active set. Used for testing."""
        self.stop()
        with self._lock:
            # Drain the queue
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            self._active.clear()

    def get_status(self) -> dict:
        """Return current queue status for debugging."""
        with self._lock:
            return {
                "queue_size": self._queue.qsize(),
                "active_count": len(self._active),
                "active_builds": list(self._active),
                "max_concurrent": self._max_concurrent,
                "worker_running": self._running,
            }

    def get_max_concurrent(self) -> int:
        """Return the current max concurrent builds limit."""
        with self._lock:
            return self._max_concurrent

    def set_max_concurrent(self, value: int) -> None:
        """Set the max concurrent builds limit."""
        with self._lock:
            self._max_concurrent = max(1, value)  # At least 1
            log.info(f"BuildQueue: max_concurrent set to {self._max_concurrent}")


# Get the default max concurrent (CPU count)
import os

_DEFAULT_MAX_CONCURRENT = os.cpu_count() or 4

# Global build queue instance - starts with default (CPU count)
_build_queue = BuildQueue(max_concurrent=_DEFAULT_MAX_CONCURRENT)

# Settings state
_build_settings = {
    "use_default_max_concurrent": True,
    "custom_max_concurrent": _DEFAULT_MAX_CONCURRENT,
}


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


def _run_build_subprocess(
    build_id: str,
    project_root: str,
    targets: list[str],
    frozen: bool = False,
    entry: str | None = None,
    standalone: bool = False,
) -> None:
    """Run ato build in a subprocess and track its status with real-time stage updates."""
    global _active_builds

    building_started_at = time.time()
    with _build_lock:
        if build_id not in _active_builds:
            log.warning(f"Build {build_id} no longer exists, aborting")
            return
        _active_builds[build_id]["status"] = "building"
        _active_builds[build_id]["building_started_at"] = building_started_at

    # Broadcast build:started event
    ws_manager.broadcast_sync(
        "builds",
        "build:started",
        {
            "build_id": build_id,
            "project_root": project_root,
            "targets": targets,
            "status": "building",
            "building_started_at": building_started_at,
        },
    )

    process = None
    final_stages: list[dict] = []
    try:
        # Build the command
        # Use --verbose to disable interactive terminal UI for subprocess capture
        cmd = ["ato", "build", "--verbose"]

        # Determine the summary.json path for real-time monitoring
        summary_path = Path(project_root) / "build" / "logs" / "latest" / "summary.json"

        # Handle standalone builds (for entry points without build config)
        if standalone and entry:
            # For standalone builds, pass the entry point as the first argument
            cmd.append(entry)
            cmd.append("--standalone")

            # Create logs directory for standalone builds
            # Standalone builds create their output in standalone_{filename}/build
            # We'll create a logs directory in there for consistency
            entry_file = entry.split(":")[0] if ":" in entry else entry
            entry_stem = Path(entry_file).stem
            standalone_dir = (
                Path(project_root) / f"standalone_{entry_stem}" / "build" / "logs"
            )
            standalone_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"Created standalone logs directory: {standalone_dir}")
            # Update summary path for standalone builds
            summary_path = standalone_dir.parent / "logs" / "latest" / "summary.json"
        else:
            # Standard project build
            # Add targets if specified
            for target in targets:
                cmd.extend(["--build", target])

        if frozen:
            cmd.append("--frozen")

        log.info(f"Running build {build_id}: {' '.join(cmd)} in {project_root}")

        # Run the build using Popen for cancellation support
        # Use DEVNULL for stdout since we get real-time status from summary.json
        # Capture stderr for error messages
        process = subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Store process reference for cancellation
        with _build_lock:
            if build_id not in _active_builds:
                log.warning(f"Build {build_id} was cleared, terminating subprocess")
                process.terminate()
                return
            _active_builds[build_id]["process"] = process

        # Poll for completion while monitoring summary.json for real-time updates
        last_stages: list[dict] = []
        poll_interval = 0.5  # 500ms polling interval
        max_wait_time = 600  # 10 minute timeout
        elapsed_time = 0.0
        stderr_chunks: list[str] = []

        # Start thread to drain stderr to prevent blocking
        def drain_stderr():
            """Drain stderr in background to prevent pipe buffer from filling."""
            while True:
                try:
                    if process.stderr is None:
                        break
                    # Use select to check if data is available (non-blocking)
                    ready, _, _ = select.select([process.stderr], [], [], 0.1)
                    if ready:
                        chunk = process.stderr.read(4096)
                        if chunk:
                            stderr_chunks.append(chunk)
                        else:
                            break  # EOF
                    elif process.poll() is not None:
                        # Process exited, read any remaining data
                        remaining = process.stderr.read()
                        if remaining:
                            stderr_chunks.append(remaining)
                        break
                except Exception:
                    break

        stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
        stderr_thread.start()

        while process.poll() is None:
            # Check for cancellation or cleanup
            with _build_lock:
                if build_id not in _active_builds:
                    log.warning(f"Build {build_id} was cleared, terminating subprocess")
                    process.terminate()
                    return
                if _active_builds[build_id].get("status") == "cancelled":
                    log.info(f"Build {build_id} was cancelled during execution")
                    return

            time.sleep(poll_interval)
            elapsed_time += poll_interval

            # Check timeout
            if elapsed_time >= max_wait_time:
                process.kill()
                raise subprocess.TimeoutExpired(cmd, max_wait_time)

            # Monitor summary.json for stage updates
            try:
                if summary_path.exists():
                    summary_data = json.loads(summary_path.read_text())
                    current_build = _find_build_in_summary(summary_data, targets, entry)
                    if current_build:
                        new_stages = current_build.get("stages", [])
                        # Broadcast changes
                        _broadcast_stage_changes(build_id, last_stages, new_stages)
                        last_stages = new_stages
                        # Update active build with current stages
                        with _build_lock:
                            if build_id in _active_builds:
                                _active_builds[build_id]["stages"] = new_stages
            except (json.JSONDecodeError, IOError):
                # Summary file may be mid-write, ignore errors
                pass

        # Process completed - get return code and collected stderr
        returncode = process.returncode

        # Wait for stderr drain thread to finish
        stderr_thread.join(timeout=2.0)
        stderr_output = "".join(stderr_chunks)

        # Read final summary to get complete stages, warnings, and errors
        final_warnings = 0
        final_errors = 0
        try:
            if summary_path.exists():
                final_summary = json.loads(summary_path.read_text())
                final_build = _find_build_in_summary(final_summary, targets, entry)
                if final_build:
                    final_stages = final_build.get("stages", [])
                    final_warnings = final_build.get("warnings", 0)
                    final_errors = final_build.get("errors", 0)
                    # Broadcast any final stage changes
                    _broadcast_stage_changes(build_id, last_stages, final_stages)
        except (json.JSONDecodeError, IOError):
            pass

        # Check if build was cancelled or cleared
        with _build_lock:
            if build_id not in _active_builds:
                log.warning(f"Build {build_id} was cleared during execution")
                return
            if _active_builds[build_id].get("status") == "cancelled":
                log.info(f"Build {build_id} was cancelled")
                return

            _active_builds[build_id]["return_code"] = returncode
            _active_builds[build_id]["process"] = None  # Clear process reference
            _active_builds[build_id]["stages"] = final_stages
            _active_builds[build_id]["warnings"] = final_warnings
            _active_builds[build_id]["errors"] = final_errors
            if returncode == 0:
                _active_builds[build_id]["status"] = "success"
            else:
                _active_builds[build_id]["status"] = "failed"
                _active_builds[build_id]["error"] = (
                    stderr_output[:1000] if stderr_output else None
                )
            # Save to build history while we have the lock
            save_build_to_history(build_id, _active_builds[build_id])

        log.info(f"Build {build_id} completed with code {returncode}")

        # Broadcast build:completed event with stages
        ws_manager.broadcast_sync(
            "builds",
            "build:completed",
            {
                "build_id": build_id,
                "project_root": project_root,
                "targets": targets,
                "status": "success" if returncode == 0 else "failed",
                "return_code": returncode,
                "stages": final_stages,
                "warnings": final_warnings,
                "errors": final_errors,
            },
        )

    except subprocess.TimeoutExpired:
        log.error(f"Build {build_id} timed out")
        with _build_lock:
            if build_id in _active_builds:
                _active_builds[build_id]["status"] = "failed"
                _active_builds[build_id]["error"] = "Build timed out after 10 minutes"
                _active_builds[build_id]["process"] = None
                _active_builds[build_id]["stages"] = final_stages
                save_build_to_history(build_id, _active_builds[build_id])

        # Broadcast build:completed event (timeout)
        ws_manager.broadcast_sync(
            "builds",
            "build:completed",
            {
                "build_id": build_id,
                "project_root": project_root,
                "targets": targets,
                "status": "failed",
                "error": "Build timed out after 10 minutes",
                "stages": final_stages,
            },
        )

    except Exception as e:
        log.error(f"Build {build_id} failed: {e}")
        with _build_lock:
            if build_id in _active_builds:
                _active_builds[build_id]["status"] = "failed"
                _active_builds[build_id]["error"] = str(e)
                _active_builds[build_id]["process"] = None
                _active_builds[build_id]["stages"] = final_stages
                save_build_to_history(build_id, _active_builds[build_id])

        # Broadcast build:completed event (error)
        ws_manager.broadcast_sync(
            "builds",
            "build:completed",
            {
                "build_id": build_id,
                "project_root": project_root,
                "targets": targets,
                "status": "failed",
                "error": str(e),
                "stages": final_stages,
            },
        )


def cancel_build(build_id: str) -> bool:
    """
    Cancel a running build by terminating its subprocess.

    Returns True if the build was cancelled, False if not found or already completed.
    """
    with _build_lock:
        if build_id not in _active_builds:
            return False

        build_info = _active_builds[build_id]

        # Check if already completed
        if build_info["status"] not in ("queued", "building"):
            return False

        # Mark as cancelled
        build_info["status"] = "cancelled"
        build_info["error"] = "Build cancelled by user"

        # Terminate the process if running
        process = build_info.get("process")
        if process and process.poll() is None:
            try:
                process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()  # Force kill if it doesn't terminate
                log.info(f"Terminated process for build {build_id}")
            except Exception as e:
                log.error(f"Error terminating build {build_id}: {e}")

        build_info["process"] = None

    # Broadcast cancellation event
    ws_manager.broadcast_sync(
        "builds",
        "build:completed",
        {
            "build_id": build_id,
            "status": "cancelled",
            "error": "Build cancelled by user",
        },
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
    projects: list[Project] = []
    seen_roots: set[str] = set()

    for root_path in paths:
        if not root_path.exists():
            log.warning(f"Path does not exist: {root_path}")
            continue

        # Find all ato.yaml files
        if (root_path / "ato.yaml").exists():
            ato_files = [root_path / "ato.yaml"]
        else:
            ato_files = list(root_path.rglob("ato.yaml"))

        for ato_file in ato_files:
            # Skip .ato/modules (dependencies)
            if ".ato" in ato_file.parts:
                continue

            project_root = ato_file.parent
            root_str = str(project_root)

            # Skip duplicates
            if root_str in seen_roots:
                continue
            seen_roots.add(root_str)

            # Parse ato.yaml to get build targets
            try:
                with open(ato_file, "r") as f:
                    data = yaml.safe_load(f)

                if not data or "builds" not in data:
                    continue

                targets: list[BuildTarget] = []
                for name, config in data.get("builds", {}).items():
                    if isinstance(config, dict):
                        targets.append(
                            BuildTarget(
                                name=name,
                                entry=config.get("entry", ""),
                                root=root_str,
                            )
                        )

                if targets:
                    projects.append(
                        Project(
                            root=root_str,
                            name=project_root.name,
                            targets=targets,
                        )
                    )

            except Exception as e:
                log.warning(f"Failed to parse {ato_file}: {e}")
                continue

    # Sort by name
    projects.sort(key=lambda p: p.name.lower())
    return projects


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

    # Set up WebSocket manager with database path
    db_path = logs_base / "build_logs.db" if logs_base else None
    ws_manager.set_paths(db_path, logs_base)

    # Capture event loop on startup for background thread broadcasts
    @app.on_event("startup")
    async def capture_event_loop():
        """Store the main event loop for use in background threads."""
        loop = asyncio.get_running_loop()
        ws_manager.set_event_loop(loop)
        log.info("Event loop captured for WebSocket broadcasts")

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

    @app.get("/api/summary")
    async def get_summary():
        """
        Return the current build summary, including any active builds.

        Aggregates build summaries from all discovered projects in the workspace.
        Each project's build/logs/latest/summary.json is read and merged.
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

        # Then, scan all workspace projects for their summaries
        workspace_paths = state.get("workspace_paths", [])
        projects = discover_projects_in_paths(workspace_paths)

        for project in projects:
            project_root = Path(project.root)
            project_summary = (
                project_root / "build" / "logs" / "latest" / "summary.json"
            )

            if project_summary.exists():
                try:
                    data = json.loads(project_summary.read_text())
                    if "builds" in data:
                        # Add project name to each build for context
                        for build in data["builds"]:
                            # Mark stale "building"/"queued" statuses from disk as failed
                            # These are only valid if tracked in _active_builds
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
                                build["display_name"] = (
                                    f"{project.name}:{build['name']}"
                                )
                        all_builds.extend(data["builds"])
                    if "totals" in data:
                        for key in totals:
                            totals[key] += data["totals"].get(key, 0)
                except (json.JSONDecodeError, Exception) as e:
                    log.warning(f"Failed to read summary from {project_summary}: {e}")

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
                    else ", ".join(targets) if targets else "default"
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
                message=f"Build already in progress",
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
                    else ", ".join(targets) if targets else "default"
                )

                builds.append({
                    # Core fields for the queue panel
                    "build_id": bid,
                    "status": status,
                    "project_root": b["project_root"],
                    "targets": targets,
                    "entry": b.get("entry"),
                    # Display-ready fields
                    "project_name": project_name,
                    "display_name": f"{project_name}:{target_name}",
                    # Timing - use building_started_at for builds, started_at for queued
                    "started_at": b.get("building_started_at") or b.get("started_at"),
                    "elapsed_seconds": elapsed,
                    # Stage data for progress display
                    "stages": b.get("stages", []),
                    # Queue position (1-indexed)
                    "queue_position": b.get("queue_position"),
                    # Error info if any
                    "error": b.get("error"),
                })

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
        project_root: Optional[str] = Query(
            None, description="Filter by project root"
        ),
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
        build_name: Optional[str] = Query(None, description="Filter by build name"),
        stage: Optional[str] = Query(None, description="Filter by build stage"),
        level: Optional[str] = Query(
            None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR)"
        ),
        audience: Optional[str] = Query(
            None, description="Filter by audience (user, developer, agent)"
        ),
        limit: int = Query(1000, ge=1, le=10000, description="Maximum results"),
        offset: int = Query(0, ge=0, description="Result offset for pagination"),
    ):
        """
        Query logs from SQLite with optional filters.

        Returns structured log entries from the build_logs.db database.
        """
        try:
            summary_path = state["summary_file"]
            if summary_path is None or not summary_path.exists():
                raise HTTPException(status_code=404, detail="No summary file found")

            summary = json.loads(summary_path.read_text())

            # If build_name specified, find its log_dir
            # Otherwise, query all builds' logs
            log_dirs: list[Path] = []
            for build in summary.get("builds", []):
                if (
                    build_name is None
                    or build.get("name") == build_name
                    or build.get("display_name") == build_name
                ):
                    if log_dir := build.get("log_dir"):
                        log_dirs.append(Path(log_dir))

            if not log_dirs:
                if build_name:
                    raise HTTPException(
                        status_code=404, detail=f"Build not found: {build_name}"
                    )
                return {"logs": [], "total": 0}

            # Collect logs from all matching builds
            all_logs: list[dict] = []
            for log_dir in log_dirs:
                db_path = log_dir / "build_logs.db"
                if not db_path.exists():
                    continue

                try:
                    conn = sqlite3.connect(str(db_path), timeout=5.0)
                    conn.row_factory = sqlite3.Row

                    # Build query with filters
                    conditions = []
                    params: list = []

                    if stage:
                        conditions.append("stage = ?")
                        params.append(stage)
                    if level:
                        conditions.append("level = ?")
                        params.append(level.upper())
                    if audience:
                        conditions.append("audience = ?")
                        params.append(audience.lower())

                    where_clause = (
                        "WHERE " + " AND ".join(conditions) if conditions else ""
                    )

                    # Query with pagination
                    query = f"""
                        SELECT id, timestamp, stage, level, level_no, audience,
                               message, ato_traceback, python_traceback
                        FROM logs
                        {where_clause}
                        ORDER BY id DESC
                        LIMIT ? OFFSET ?
                    """
                    params.extend([limit, offset])

                    cursor = conn.execute(query, params)
                    rows = cursor.fetchall()

                    for row in rows:
                        all_logs.append(
                            {
                                "id": row["id"],
                                "timestamp": row["timestamp"],
                                "stage": row["stage"],
                                "level": row["level"],
                                "level_no": row["level_no"],
                                "audience": row["audience"],
                                "message": row["message"],
                                "ato_traceback": row["ato_traceback"],
                                "python_traceback": row["python_traceback"],
                                "build_dir": str(log_dir),
                            }
                        )

                    conn.close()
                except sqlite3.Error as e:
                    log.warning(f"Error reading logs from {db_path}: {e}")
                    continue

            # Sort by timestamp descending and apply limit
            all_logs.sort(key=lambda x: x["timestamp"], reverse=True)
            return {"logs": all_logs[:limit], "total": len(all_logs)}

        except HTTPException:
            raise
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
        from atopile import version

        parent_dir = Path(request.parent_directory)
        if not parent_dir.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Parent directory does not exist: {request.parent_directory}",
            )

        if not parent_dir.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Path is not a directory: {request.parent_directory}",
            )

        # Generate project name if not provided
        if request.name:
            project_name = request.name
        else:
            # Find a unique name like "new-project", "new-project-2", etc.
            base_name = "new-project"
            project_name = base_name
            counter = 2
            while (parent_dir / project_name).exists():
                project_name = f"{base_name}-{counter}"
                counter += 1

        project_dir = parent_dir / project_name

        # Check if directory already exists
        if project_dir.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Directory already exists: {project_dir}",
            )

        try:
            # Create project directory
            project_dir.mkdir(parents=True)

            # Create layouts directory
            (project_dir / "layouts").mkdir()

            # Get atopile version
            try:
                ato_version = version.get_installed_atopile_version()
            except Exception:
                ato_version = "^0.9.0"  # Fallback

            # Create ato.yaml
            ato_yaml_content = f'''requires-atopile: "{ato_version}"

paths:
  src: ./
  layout: ./layouts

builds:
  default:
    entry: main.ato:App
'''
            (project_dir / "ato.yaml").write_text(ato_yaml_content)

            # Create main.ato
            main_ato_content = f'''"""{project_name} - A new atopile project"""

module App:
    pass
'''
            (project_dir / "main.ato").write_text(main_ato_content)

            # Create .gitignore
            gitignore_content = """# Build outputs
build/

# Dependencies
.ato/

# IDE
.vscode/
.idea/

# OS
.DS_Store
"""
            (project_dir / ".gitignore").write_text(gitignore_content)

            log.info(f"Created new project: {project_dir}")

            return CreateProjectResponse(
                success=True,
                message=f"Created project '{project_name}'",
                project_root=str(project_dir),
                project_name=project_name,
            )

        except Exception as e:
            # Clean up if creation failed
            if project_dir.exists():
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
