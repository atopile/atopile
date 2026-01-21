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
from atopile.server.domains import artifacts as artifacts_domain
from atopile.server.domains import packages as packages_domain
from atopile.server import project_discovery
from atopile.server.app_context import AppContext
from atopile.server.file_watcher import PollingFileWatcher
from atopile.server.state import server_state
from atopile.logging import BuildLogger

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

    def _query_logs_sync(self, filters: dict) -> tuple[list[dict], int]:
        """
        Blocking helper to query logs from SQLite database.
        Returns (logs_list, limit).
        """
        if not self._db_path or not self._db_path.exists():
            return [], filters.get("limit", 100)

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

        return logs, limit

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
            # Run blocking DB query in thread pool
            logs, limit = await asyncio.to_thread(self._query_logs_sync, filters)

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


async def _load_projects_background(ctx: AppContext) -> None:
    """Background task to load projects without blocking startup."""
    from atopile.server.state import Project as StateProject
    from atopile.server.state import BuildTarget as StateBuildTarget

    try:
        log.info(f"[background] Loading projects from {len(ctx.workspace_paths)} paths")
        # Run blocking discovery in thread pool
        projects = await asyncio.to_thread(
            project_discovery.discover_projects_in_paths, ctx.workspace_paths
        )
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
        log.info(f"[background] Loaded {len(state_projects)} projects")
    except Exception as exc:
        log.error(f"[background] Failed to load projects: {exc}")
        await server_state.set_projects([], error=str(exc))


async def _load_packages_background(ctx: AppContext) -> None:
    """Background task to load packages without blocking startup."""
    try:
        log.info("[background] Loading packages from registry")
        # Use refresh_packages_state which properly loads installed + registry packages
        await packages_domain.refresh_packages_state(scan_paths=ctx.workspace_paths)
        log.info(f"[background] Loaded {len(server_state.state.packages)} packages")
    except Exception as exc:
        log.error(f"[background] Failed to load packages: {exc}")
        await server_state.set_packages([], error=str(exc))


async def _refresh_stdlib_state() -> None:
    from atopile.server.state import StdLibItem as StateStdLibItem
    from atopile.server import stdlib as stdlib_domain

    # Run blocking stdlib refresh in thread pool
    items = await asyncio.to_thread(stdlib_domain.refresh_standard_library)
    state_items = [StateStdLibItem.model_validate(item.model_dump()) for item in items]
    await server_state.set_stdlib_items(state_items)


async def _refresh_bom_state() -> None:
    selected = server_state._state.selected_project_root
    if not selected:
        return

    target_names = server_state._state.selected_target_names or []
    target = target_names[0] if target_names else "default"

    try:
        # Run blocking BOM fetch in thread pool
        bom_json = await asyncio.to_thread(
            artifacts_domain.handle_get_bom, selected, target
        )
    except Exception as exc:
        await server_state.set_bom_data(None, str(exc))
        return

    if bom_json is None:
        await server_state.set_bom_data(None, "BOM not found. Run build first.")
        return

    await server_state.set_bom_data(bom_json)


async def _refresh_variables_state() -> None:
    selected = server_state._state.selected_project_root
    if not selected:
        return

    target_names = server_state._state.selected_target_names or []
    target = target_names[0] if target_names else "default"

    try:
        # Run blocking variables fetch in thread pool
        variables_json = await asyncio.to_thread(
            artifacts_domain.handle_get_variables, selected, target
        )
    except Exception as exc:
        await server_state.set_variables_data(None, str(exc))
        return

    if variables_json is None:
        await server_state.set_variables_data(
            None, "Variables not found. Run build first."
        )
        return

    await server_state.set_variables_data(variables_json)


async def _watch_stdlib_background() -> None:
    from atopile.server import stdlib as stdlib_domain

    watcher = PollingFileWatcher(
        "stdlib",
        paths=stdlib_domain.get_stdlib_watch_paths(),
        on_change=lambda _result: _refresh_stdlib_state(),
        interval_s=1.0,
    )
    await watcher.run()


async def _watch_bom_background() -> None:
    def _paths() -> list[Path]:
        projects = server_state._state.projects or []
        return [
            Path(project.root) / "build" / "builds"
            for project in projects
            if project.root
        ]

    watcher = PollingFileWatcher(
        "bom",
        paths_provider=_paths,
        on_change=lambda _result: _refresh_bom_state(),
        glob="**/*.bom.json",
        interval_s=1.0,
    )
    await watcher.run()


async def _watch_variables_background() -> None:
    def _paths() -> list[Path]:
        projects = server_state._state.projects or []
        return [
            Path(project.root) / "build" / "builds"
            for project in projects
            if project.root
        ]

    watcher = PollingFileWatcher(
        "variables",
        paths_provider=_paths,
        on_change=lambda _result: _refresh_variables_state(),
        glob="**/*.variables.json",
        interval_s=1.0,
    )
    await watcher.run()


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

    db_path = BuildLogger.get_log_db()
    ws_manager.set_paths(db_path, logs_base)

    if logs_base:
        build_history_db_path = logs_base / "build_history.db"
        init_build_history_db(build_history_db_path)

    @app.on_event("startup")
    async def on_startup():
        loop = asyncio.get_running_loop()

        # Configure a larger thread pool for asyncio.to_thread() to prevent exhaustion
        # Default is min(32, os.cpu_count() + 4), we increase it
        from concurrent.futures import ThreadPoolExecutor

        executor = ThreadPoolExecutor(max_workers=64, thread_name_prefix="ato_server_")
        loop.set_default_executor(executor)
        log.info("Configured thread pool with 64 workers")

        ws_manager.set_event_loop(loop)
        server_state.set_event_loop(loop)
        server_state.set_workspace_paths(ctx.workspace_paths)

        asyncio.create_task(_refresh_stdlib_state())
        asyncio.create_task(_watch_stdlib_background())
        asyncio.create_task(_watch_bom_background())
        asyncio.create_task(_watch_variables_background())

        if not ctx.workspace_paths:
            log.info("No workspace paths configured, skipping initial state population")
            return

        # Set loading states immediately so UI shows spinners
        await server_state.set_loading_projects(True)
        await server_state.set_loading_packages(True)

        # Fire background tasks - don't await, server starts immediately
        asyncio.create_task(_load_projects_background(ctx))
        asyncio.create_task(_load_packages_background(ctx))
        log.info("Server started - background loaders running")

    from atopile.server.routes import (
        artifacts as artifacts_routes,
        builds as builds_routes,
        logs as logs_routes,
        packages as packages_routes,
        problems as problems_routes,
        projects as projects_routes,
        websocket as ws_routes,
    )

    app.include_router(ws_routes.router)
    app.include_router(projects_routes.router)
    app.include_router(builds_routes.router)
    app.include_router(logs_routes.router)
    app.include_router(artifacts_routes.router)
    app.include_router(problems_routes.router)
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
            # Increase WebSocket max message size to 10MB (default is 1MB)
            # Needed because state (especially stdlibItems) can be large
            ws_max_size=10 * 1024 * 1024,
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
