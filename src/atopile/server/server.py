"""
FastAPI server for the build dashboard API.

Provides API endpoints for build data. The React frontend is served
directly by VS Code webview for better IDE integration.
"""

import asyncio
import logging
import socket
import threading
import time
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atopile.server import build_history, project_discovery
from atopile.server.app_context import AppContext
from atopile.server.domains import artifacts as artifacts_domain
from atopile.server.domains import packages as packages_domain
from atopile.server.file_watcher import PollingFileWatcher
from atopile.server.state import server_state

log = logging.getLogger(__name__)

# Fixed port for the dashboard server - extension opens this directly
DASHBOARD_PORT = 8501

init_build_history_db = build_history.init_build_history_db


async def _load_projects_background(ctx: AppContext) -> None:
    """Background task to load projects without blocking startup."""
    from atopile.dataclasses import BuildTarget as StateBuildTarget
    from atopile.dataclasses import Project as StateProject

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
                    StateBuildTarget(
                        name=t.name,
                        entry=t.entry,
                        root=t.root,
                        last_build=t.last_build,
                    )
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
    from atopile.dataclasses import StdLibItem as StateStdLibItem
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


async def _load_atopile_install_options() -> None:
    """Background task to load atopile versions, branches, and detect installations."""
    from atopile.server.domains import atopile_install

    try:
        log.info("[background] Loading atopile installation options")

        # Fetch available versions from PyPI
        versions = await atopile_install.fetch_available_versions()
        await server_state.set_atopile_available_versions(versions)
        log.info(f"[background] Loaded {len(versions)} PyPI versions")

        # Fetch available branches from GitHub
        branches = await atopile_install.fetch_available_branches()
        await server_state.set_atopile_available_branches(branches)
        log.info(f"[background] Loaded {len(branches)} GitHub branches")

        # Detect local installations
        installations = await asyncio.to_thread(
            atopile_install.detect_local_installations
        )
        await server_state.set_atopile_detected_installations(installations)
        log.info(f"[background] Detected {len(installations)} local installations")

    except Exception as exc:
        log.error(f"[background] Failed to load atopile install options: {exc}")


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

        server_state.set_event_loop(loop)
        server_state.set_workspace_paths(ctx.workspace_paths)

        asyncio.create_task(_refresh_stdlib_state())
        asyncio.create_task(_watch_stdlib_background())
        asyncio.create_task(_watch_bom_background())
        asyncio.create_task(_watch_variables_background())
        asyncio.create_task(_load_atopile_install_options())

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
    )
    from atopile.server.routes import (
        builds as builds_routes,
    )
    from atopile.server.routes import (
        logs as logs_routes,
    )
    from atopile.server.routes import (
        packages as packages_routes,
    )
    from atopile.server.routes import (
        parts as parts_routes,
    )
    from atopile.server.routes import (
        problems as problems_routes,
    )
    from atopile.server.routes import (
        projects as projects_routes,
    )
    from atopile.server.routes import (
        websocket as ws_routes,
    )

    app.include_router(ws_routes.router)
    app.include_router(logs_routes.router)
    app.include_router(projects_routes.router)
    app.include_router(builds_routes.router)
    app.include_router(artifacts_routes.router)
    app.include_router(parts_routes.router)
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
