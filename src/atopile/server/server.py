"""
FastAPI server for the build dashboard API.

Provides API endpoints for build data. The React frontend is served
directly by VS Code webview for better IDE integration.
"""

import asyncio
import logging
import os
import socket
import threading
import time
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atopile.dataclasses import AppContext, EventType
from atopile.model.build_queue import _build_queue
from atopile.model.model_state import model_state
from atopile.model.sqlite import BuildHistory
from atopile.server.connections import server_state
from atopile.server.core import projects as core_projects
from atopile.server.domains import packages as packages_domain
from atopile.server.events import event_bus
from atopile.server.file_watcher import FileChangeResult, FileWatcher

log = logging.getLogger(__name__)

# Fixed port for the dashboard server - extension opens this directly
UI_DEBOUNCE_S = float(os.getenv("ATOPILE_UI_DEBOUNCE_S", "0.5"))
PACKAGES_REFRESH_MIN_INTERVAL_S = float(
    os.getenv("ATOPILE_PACKAGES_REFRESH_MIN_INTERVAL_S", "30")
)
_debounce_tasks: dict[str, asyncio.Task] = {}
_last_packages_registry_refresh: float = 0.0


async def _load_projects_background(ctx: AppContext) -> None:
    """Background task to load projects without blocking startup."""
    if not ctx.workspace_paths:
        await server_state.emit_event("projects_changed")
        return
    try:
        log.info(f"[background] Loading projects from {ctx.workspace_paths}")
        await asyncio.to_thread(
            core_projects.discover_projects_in_paths, ctx.workspace_paths
        )
        await server_state.emit_event("projects_changed")
        log.info("[background] Project discovery complete")
    except Exception as exc:
        log.error(f"[background] Failed to load projects: {exc}")
        await server_state.emit_event("projects_changed", {"error": str(exc)})


async def _refresh_projects_state() -> None:
    workspace_paths = model_state.workspace_paths
    if not workspace_paths:
        await server_state.emit_event("projects_changed")
        return

    try:
        await asyncio.to_thread(
            core_projects.discover_projects_in_paths, workspace_paths
        )
        await server_state.emit_event("projects_changed")
    except Exception as exc:
        log.error(f"[background] Failed to refresh projects: {exc}")
        await server_state.emit_event("projects_changed", {"error": str(exc)})


async def _load_packages_background(ctx: AppContext) -> None:
    """Background task to load packages without blocking startup."""
    try:
        log.info("[background] Loading packages from registry")
        # Use first workspace path for package scanning
        scan_path = ctx.workspace_paths[0] if ctx.workspace_paths else None
        await packages_domain.refresh_packages_state(scan_path=scan_path)
        log.info("[background] Packages refresh complete")
    except Exception as exc:
        log.error(f"[background] Failed to load packages: {exc}")
        await server_state.emit_event("packages_changed", {"error": str(exc)})


async def _refresh_stdlib_state() -> None:
    await server_state.emit_event("stdlib_changed")


async def _refresh_bom_state() -> None:
    await server_state.emit_event("bom_changed")


async def _refresh_variables_state() -> None:
    await server_state.emit_event("variables_changed")


async def _watch_stdlib_background() -> None:
    from atopile.server import stdlib as stdlib_domain

    watcher = FileWatcher(
        "stdlib",
        paths=stdlib_domain.get_stdlib_watch_paths(),
        on_change=lambda _result: _refresh_stdlib_state(),
        glob="**/*.{py,ato}",
    )
    await watcher.run()


async def _watch_bom_background() -> None:
    watcher = FileWatcher(
        "bom",
        paths_provider=_get_workspace_roots_for_watcher,
        on_change=lambda _result: _refresh_bom_state(),
        glob="**/build/builds/*.bom.json",
    )
    await watcher.run()


async def _watch_variables_background() -> None:
    watcher = FileWatcher(
        "variables",
        paths_provider=_get_workspace_roots_for_watcher,
        on_change=lambda _result: _refresh_variables_state(),
        glob="**/build/builds/*.variables.json",
    )
    await watcher.run()


def _debounce(key: str, delay_s: float, coro_factory) -> None:
    """
    Debounce a coroutine - cancel any pending task for this key and schedule a new one.

    The task will run after delay_s seconds. If called again with the same key
    before the delay expires, the previous task is cancelled and a new one is scheduled.
    """
    # Clean up any completed tasks to prevent unbounded growth
    # This is O(n) but n is small (typically < 20 keys) and runs infrequently
    done_keys = [k for k, t in _debounce_tasks.items() if t.done()]
    for k in done_keys:
        _debounce_tasks.pop(k, None)

    existing = _debounce_tasks.get(key)
    if existing and not existing.done():
        existing.cancel()

    async def _runner():
        try:
            await asyncio.sleep(delay_s)
            await coro_factory()
        except asyncio.CancelledError:
            return
        finally:
            task = _debounce_tasks.get(key)
            if task is asyncio.current_task():
                _debounce_tasks.pop(key, None)

    _debounce_tasks[key] = asyncio.create_task(_runner())


def _get_workspace_roots_for_watcher() -> list[Path]:
    """Get workspace roots as a list for file watcher compatibility."""
    root = model_state.workspace_path
    return [root] if root else []


def _is_path_in_workspace(path: Path) -> bool:
    """Check if a path is within the workspace root."""
    root = model_state.workspace_path
    if not root:
        return False
    try:
        resolved_path = path.resolve()
        resolved_root = root.resolve()
        return resolved_path.is_relative_to(resolved_root)
    except FileNotFoundError:
        return False


def _has_affected_paths(result: "FileChangeResult") -> bool:
    """Check if any changed paths are within the workspace."""
    changed_paths = result.created + result.changed + result.deleted
    if not changed_paths:
        return False
    return any(_is_path_in_workspace(p) for p in changed_paths)


async def _emit_project_files_changed() -> None:
    root = model_state.workspace_path
    if root:
        await server_state.emit_event(
            "project_files_changed", {"project_root": str(root)}
        )


async def _emit_project_modules_changed() -> None:
    root = model_state.workspace_path
    if root:
        await server_state.emit_event(
            "project_modules_changed", {"project_root": str(root)}
        )


async def _emit_project_dependencies_changed() -> None:
    root = model_state.workspace_path
    if root:
        await server_state.emit_event(
            "project_dependencies_changed", {"project_root": str(root)}
        )


async def _watch_projects_background() -> None:
    watcher = FileWatcher(
        "projects",
        paths_provider=_get_workspace_roots_for_watcher,
        on_change=lambda _result: _refresh_projects_state(),
        glob="**/ato.yaml",
    )
    await watcher.run()


async def _watch_project_sources_background() -> None:
    watcher = FileWatcher(
        "project-sources",
        paths_provider=_get_workspace_roots_for_watcher,
        on_change=lambda result: _handle_project_sources_change(result),
        glob="**/*.ato",
    )
    await watcher.run()


async def _watch_project_python_background() -> None:
    watcher = FileWatcher(
        "project-python",
        paths_provider=_get_workspace_roots_for_watcher,
        on_change=lambda result: _handle_project_python_change(result),
        glob="**/*.py",
    )
    await watcher.run()


async def _watch_project_dependencies_background() -> None:
    watcher = FileWatcher(
        "project-deps",
        paths_provider=_get_workspace_roots_for_watcher,
        on_change=lambda result: _handle_project_dependencies_change(result),
        glob="**/ato.yaml",
    )
    await watcher.run()


async def _handle_project_sources_change(
    result: "FileChangeResult",
) -> None:
    if not _has_affected_paths(result):
        return
    _debounce("project-files", UI_DEBOUNCE_S, _emit_project_files_changed)
    _debounce("project-modules", UI_DEBOUNCE_S, _emit_project_modules_changed)


async def _handle_project_python_change(
    result: "FileChangeResult",
) -> None:
    if not _has_affected_paths(result):
        return
    _debounce("project-files", UI_DEBOUNCE_S, _emit_project_files_changed)


async def _handle_project_dependencies_change(
    result: "FileChangeResult",
) -> None:
    if not _has_affected_paths(result):
        return
    _debounce("project-deps", UI_DEBOUNCE_S, _emit_project_dependencies_changed)
    _debounce("packages-refresh", UI_DEBOUNCE_S, _refresh_packages_for_deps_change)


async def _refresh_packages_for_deps_change() -> None:
    from atopile.server.domains import packages as packages_domain

    global _last_packages_registry_refresh
    now = time.time()
    if now - _last_packages_registry_refresh >= PACKAGES_REFRESH_MIN_INTERVAL_S:
        await packages_domain.refresh_packages_state()
        _last_packages_registry_refresh = time.time()
    else:
        await packages_domain.refresh_installed_packages_state()


async def _load_atopile_install_options(ctx: AppContext) -> None:
    """Background task to load atopile versions, branches, and detect installations."""
    from atopile import version as ato_version
    from atopile.server.domains import atopile_install

    try:
        log.info("[background] Loading atopile installation options")

        # Emit the ACTUAL atopile status - this is the source of truth
        # for what version/source the extension is using to build projects
        try:
            version_obj = ato_version.get_installed_atopile_version()
            actual_version = str(version_obj)
            actual_source = ctx.ato_source or "unknown"
            # Include UI source type so the dropdown shows the correct initial state
            ui_source = ctx.ato_ui_source or "release"
            await server_state.emit_event(
                "atopile_config_changed",
                {
                    "actual_version": actual_version,
                    "actual_source": actual_source,
                    "actual_binary_path": ctx.ato_binary_path,  # Actual binary path
                    "source": ui_source,  # Sets the active toggle state
                    "local_path": ctx.ato_local_path,  # Path for display in UI
                },
            )
            log.info(
                f"[background] Actual atopile: {actual_version} from {actual_source} "
                f"(binary: {ctx.ato_binary_path}, UI: {ui_source})"
            )
        except Exception as e:
            log.warning(f"[background] Could not detect actual version: {e}")

        # Fetch available versions from PyPI (for the selector UI)
        versions = await atopile_install.fetch_available_versions()
        await server_state.emit_event(
            "atopile_config_changed", {"available_versions": versions}
        )
        log.info(f"[background] Loaded {len(versions)} PyPI versions")

        # Fetch available branches from GitHub (for the selector UI)
        branches = await atopile_install.fetch_available_branches()
        await server_state.emit_event(
            "atopile_config_changed", {"available_branches": branches}
        )
        log.info(f"[background] Loaded {len(branches)} GitHub branches")

        # Detect local installations (for the selector UI)
        installations = await asyncio.to_thread(
            atopile_install.detect_local_installations
        )
        await server_state.emit_event(
            "atopile_config_changed", {"detected_installations": installations}
        )
        log.info(f"[background] Detected {len(installations)} local installations")

    except Exception as exc:
        log.error(f"[background] Failed to load atopile install options: {exc}")


def create_app(
    summary_file: Optional[Path] = None,
    workspace_paths: Optional[list[Path]] = None,
    ato_source: Optional[str] = None,
    ato_ui_source: Optional[str] = None,
    ato_local_path: Optional[str] = None,
    ato_binary_path: Optional[str] = None,
) -> FastAPI:
    """
    Create the FastAPI application with API routes for the dashboard.
    """
    app = FastAPI(title="atopile Build Server")

    # CORS configuration - allow all origins for local tooling/webviews.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "*",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    ctx = AppContext(
        summary_file=summary_file,
        workspace_paths=workspace_paths or [],
        ato_source=ato_source,
        ato_ui_source=ato_ui_source,
        ato_local_path=ato_local_path,
        ato_binary_path=ato_binary_path,
    )
    app.state.ctx = ctx

    # Initialize build history database
    BuildHistory.init_db()

    @app.on_event("startup")
    async def on_startup():
        loop = asyncio.get_running_loop()

        # Configure a larger thread pool for asyncio.to_thread() to prevent exhaustion
        # Default is min(32, os.cpu_count() + 4), we increase it
        from concurrent.futures import ThreadPoolExecutor

        executor = ThreadPoolExecutor(max_workers=64, thread_name_prefix="ato_server_")
        loop.set_default_executor(executor)
        log.info("Configured thread pool with 64 workers")

        # Configure model_state with workspace paths
        model_state.set_workspace_paths(ctx.workspace_paths)

        # Configure event_bus with event loop and emitter
        event_bus.set_event_loop(loop)
        event_bus.register_emitter(server_state.emit_event)

        from atopile.server.module_introspection import clear_module_cache

        def _handle_build_change(_build_id: str, _event: str) -> None:
            event_bus.emit_sync(EventType.BUILDS_CHANGED)

        def _handle_build_completed(build) -> None:
            clear_module_cache()
            event_bus.emit_sync(
                EventType.PROJECTS_CHANGED, {"project_root": build.project_root}
            )
            event_bus.emit_sync(
                EventType.BOM_CHANGED, {"project_root": build.project_root}
            )

        _build_queue.on_change = _handle_build_change
        _build_queue.on_completed = _handle_build_completed

        asyncio.create_task(_refresh_stdlib_state())
        asyncio.create_task(_watch_stdlib_background())
        asyncio.create_task(_watch_bom_background())
        asyncio.create_task(_watch_variables_background())
        asyncio.create_task(_watch_projects_background())
        asyncio.create_task(_watch_project_sources_background())
        asyncio.create_task(_watch_project_python_background())
        asyncio.create_task(_watch_project_dependencies_background())
        asyncio.create_task(_load_atopile_install_options(ctx))

        if not ctx.workspace_paths:
            log.info("No workspace paths configured, skipping initial state population")
            return

        # Fire background tasks - don't await, server starts immediately
        asyncio.create_task(_load_projects_background(ctx))
        asyncio.create_task(_load_packages_background(ctx))
        log.info("Server started - background loaders running")

    # Health check endpoint for extension to verify server is running
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "ok"}

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
        tests as tests_routes,
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
    app.include_router(tests_routes.router)

    return app


def find_free_port() -> int:
    """Find a free port to use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def kill_process_on_port(port: int, host: str = "127.0.0.1") -> bool:
    """
    Kill the process using the specified port.

    Uses lsof to find the process and sends SIGTERM (then SIGKILL if needed).
    Waits up to 3 seconds for the port to become available.

    Returns True if the port is now available, False otherwise.
    """
    import subprocess
    import time

    try:
        # Use lsof to find the PID using the port (works on macOS and Linux)
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return False

        pids = result.stdout.strip().split("\n")
        for pid in pids:
            try:
                subprocess.run(["kill", "-TERM", pid], check=True)
            except subprocess.CalledProcessError:
                # Try SIGKILL if SIGTERM fails
                subprocess.run(["kill", "-KILL", pid], check=False)

        # Wait for port to become available
        for _ in range(30):  # Wait up to 3 seconds
            if not is_port_in_use(port, host):
                return True
            time.sleep(0.1)

        return not is_port_in_use(port, host)
    except FileNotFoundError:
        # lsof not available
        return False


class DashboardServer:
    """Manages the dashboard server lifecycle."""

    def __init__(
        self,
        port: Optional[int] = None,
        workspace_paths: Optional[list[Path]] = None,
        ato_source: Optional[str] = None,
        ato_ui_source: Optional[str] = None,
        ato_local_path: Optional[str] = None,
        ato_binary_path: Optional[str] = None,
    ):
        self.port = port or find_free_port()
        self.workspace_paths = workspace_paths or []
        self.app = create_app(
            workspace_paths=self.workspace_paths,
            ato_source=ato_source,
            ato_ui_source=ato_ui_source,
            ato_local_path=ato_local_path,
            ato_binary_path=ato_binary_path,
        )
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
            ws_max_size=2 * 1024 * 1024,
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
    port: Optional[int] = None,
    workspace_paths: Optional[list[Path]] = None,
) -> tuple[DashboardServer, str]:
    """
    Start the dashboard server.

    Args:
        port: Port to use (defaults to a free port)
        workspace_paths: Workspace paths to scan for projects

    Returns:
        Tuple of (DashboardServer, url)
    """
    server = DashboardServer(port=port, workspace_paths=workspace_paths)
    server.start()
    return server, server.url
