"""
FastAPI server for the build dashboard API.

Provides API endpoints for build data. The React frontend is served
directly by VS Code webview for better IDE integration.
"""

import asyncio
import logging
import socket
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

from atopile.server import build_history
from atopile.server import build_queue
from atopile.server.domains import packages as packages_domain
from atopile.server import project_discovery
from atopile.server.app_context import AppContext
from atopile.server.state import server_state
from atopile.logging import get_central_log_db

log = logging.getLogger(__name__)

init_build_history_db = build_history.init_build_history_db


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
build_queue.set_broadcast_sync(ws_manager.broadcast_sync)


async def _populate_initial_state(ctx: AppContext) -> None:
    """Populate server state with projects and packages on startup."""
    if not ctx.workspace_paths:
        log.info("No workspace paths configured, skipping initial state population")
        return

    log.info(
        f"Populating initial state from {len(ctx.workspace_paths)} workspace paths"
    )

    from atopile.server.state import Project as StateProject
    from atopile.server.state import BuildTarget as StateBuildTarget
    from atopile.server.state import PackageInfo as StatePackageInfo

    try:
        projects = project_discovery.discover_projects_in_paths(ctx.workspace_paths)
        state_projects = [
            StateProject(
                root=project.root,
                name=project.name,
                targets=[
                    StateBuildTarget(name=t.name, entry=t.entry, root=t.root)
                    for t in project.targets
                ],
            )
            for project in projects
        ]
        await server_state.set_projects(state_projects)
        log.info(f"Loaded {len(state_projects)} projects")
    except Exception as exc:
        log.error(f"Failed to load projects: {exc}")

    try:
        installed = packages_domain.get_all_installed_packages(ctx.workspace_paths)
        enriched = packages_domain.enrich_packages_with_registry(installed)

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
                has_update=packages_domain.version_is_newer(
                    p.version, p.latest_version
                ),
                downloads=p.downloads,
                version_count=p.version_count,
                keywords=p.keywords or [],
            )
            for p in enriched.values()
        ]
        await server_state.set_packages(state_packages)
        log.info(f"Loaded {len(state_packages)} packages")
    except Exception as exc:
        log.error(f"Failed to load packages: {exc}")










def create_app(
    summary_file: Optional[Path] = None,
    logs_base: Optional[Path] = None,
    workspace_paths: Optional[list[Path]] = None,
) -> FastAPI:
    """
    Create the FastAPI application with API routes for the dashboard.
    """
    app = FastAPI(title="atopile Build Server")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    ctx = AppContext(
        summary_file=summary_file,
        logs_base=logs_base,
        workspace_paths=workspace_paths or [],
    )
    app.state.ctx = ctx

    db_path = get_central_log_db()
    ws_manager.set_paths(db_path, logs_base)

    if logs_base:
        build_history_db_path = logs_base / "build_history.db"
        init_build_history_db(build_history_db_path)

    @app.on_event("startup")
    async def capture_event_loop():
        loop = asyncio.get_running_loop()
        ws_manager.set_event_loop(loop)
        server_state.set_event_loop(loop)
        server_state.set_workspace_paths(ctx.workspace_paths)
        await _populate_initial_state(ctx)

    from atopile.server.domains import builds, logs, problems, projects, resolve, stdlib, artifacts
    from atopile.server.routes import packages as packages_routes
    from atopile.server.routes import websocket as ws_routes

    app.include_router(ws_routes.router)
    app.include_router(projects.router)
    app.include_router(builds.router)
    app.include_router(logs.router)
    app.include_router(artifacts.router)
    app.include_router(resolve.router)
    app.include_router(problems.router)
    app.include_router(stdlib.router)
    app.include_router(packages_routes.router)

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
