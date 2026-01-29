"""
FastAPI server for the build dashboard API.

Provides API endpoints for build data. The React frontend is served
directly by VS Code webview for better IDE integration.

Usage:
    python -m atopile.server --port PORT [--workspace PATH]

Exception Contract:
    - Build exceptions run in subprocesses and mark builds as FAILED
    - Server exceptions crash the entire server process (not just HTTP 500)
    - This ensures visibility of unexpected errors

Exit Codes:
    0 - Clean shutdown (Ctrl+C or SIGTERM)
    1 - Startup error (port in use, config error)
    2 - Server crash (unhandled exception during operation)
"""

import asyncio
import atexit
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

import requests
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

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
    # No try/except - let exceptions crash the server for visibility
    log.info(f"Loading projects from {ctx.workspace_paths}")
    await asyncio.to_thread(
        core_projects.discover_projects_in_paths, ctx.workspace_paths
    )
    await server_state.emit_event("projects_changed")
    log.info("Project discovery complete")


async def _refresh_projects_state() -> None:
    workspace_paths = model_state.workspace_paths
    if not workspace_paths:
        await server_state.emit_event("projects_changed")
        return

    # No try/except - let exceptions crash the server for visibility
    await asyncio.to_thread(
        core_projects.discover_projects_in_paths, workspace_paths
    )
    await server_state.emit_event("projects_changed")


async def _load_packages_background(ctx: AppContext) -> None:
    """Background task to load packages without blocking startup."""
    # No try/except - let exceptions crash the server for visibility
    log.info("Loading packages from registry")
    # Use first workspace path for package scanning
    scan_path = ctx.workspace_paths[0] if ctx.workspace_paths else None
    await packages_domain.refresh_packages_state(scan_path=scan_path)
    log.info("Packages refresh complete")


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

    # No try/except - let exceptions crash the server for visibility
    log.info("Loading atopile installation options")

    # Fetch available versions from PyPI
    versions = await atopile_install.fetch_available_versions()
    await server_state.emit_event(
        "atopile_config_changed", {"available_versions": versions}
    )
    log.info(f"Loaded {len(versions)} PyPI versions")

    # Detect local installations
    installations = await asyncio.to_thread(
        atopile_install.detect_local_installations
    )
    await server_state.emit_event(
        "atopile_config_changed", {"detected_installations": installations}
    )
    log.info(f"Detected {len(installations)} local installations")


def cleanup_server(exc: BaseException | None = None) -> None:
    """
    Cleanup server resources before exit.

    Call this before any exit to ensure:
    1. Build subprocesses are stopped
    2. Logs are flushed to database
    3. Telemetry is captured and flushed

    All steps are best-effort - failures don't prevent other cleanup.
    """
    # 1. Stop build subprocesses
    try:
        _build_queue.stop()
    except Exception:
        pass

    # 2. Flush logs to database
    try:
        from atopile.logging import BuildLogger
        BuildLogger.close_all()
    except Exception:
        pass

    # 3. Capture exception for telemetry (if provided)
    try:
        from atopile import telemetry
        if exc:
            telemetry.capture_exception(exc)
        telemetry._flush_telemetry_on_exit()
    except Exception:
        pass

    # 4. Flush logging handlers
    try:
        logging.shutdown()
    except Exception:
        pass


def _fatal_error(msg: str, exc: BaseException | None = None) -> None:
    """
    Log fatal error, cleanup, and terminate the server process.

    Uses os._exit() to ensure the process dies even if FastAPI/uvicorn
    would otherwise swallow the exception.
    """
    log.critical("FATAL SERVER ERROR: %s", msg)
    if exc:
        log.critical("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))

    cleanup_server(exc)

    # Exit code 2 distinguishes server crash from build failure (exit 1)
    os._exit(2)


class CrashOnErrorMiddleware(BaseHTTPMiddleware):
    """
    Middleware that crashes the server on unhandled exceptions.

    Instead of returning HTTP 500, this terminates the process so that
    server bugs are visible and don't silently degrade service.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            # Let HTTPException through - those are intentional error responses
            from fastapi import HTTPException

            if isinstance(exc, HTTPException):
                raise
            _fatal_error(f"Unhandled exception in route {request.url.path}", exc)
            raise  # Unreachable, but keeps type checker happy


def _asyncio_exception_handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """
    Handle uncaught exceptions in asyncio tasks by crashing the server.

    This ensures background task failures are visible instead of being
    silently logged and ignored.
    """
    exc = context.get("exception")
    msg = context.get("message", "Unknown asyncio error")

    # Log the full context for debugging
    log.critical("Uncaught exception in asyncio task: %s", msg)
    if exc:
        _fatal_error(f"Asyncio task crashed: {msg}", exc)
    else:
        _fatal_error(f"Asyncio task error: {msg}")


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

    Exception Handling:
        - Unhandled exceptions in routes → server crashes (not HTTP 500)
        - Unhandled exceptions in background tasks → server crashes
        - HTTPException → proper HTTP error response (intentional)
    """
    app = FastAPI(title="atopile Build Server")

    # Add crash-on-error middleware FIRST (innermost)
    app.add_middleware(CrashOnErrorMiddleware)

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

        # Install exception handler that crashes server on unhandled task exceptions
        loop.set_exception_handler(_asyncio_exception_handler)

        # Configure a larger thread pool for asyncio.to_thread() to prevent exhaustion
        # Default is min(32, os.cpu_count() + 4), we increase it
        from concurrent.futures import ThreadPoolExecutor

        executor = ThreadPoolExecutor(max_workers=64, thread_name_prefix="ato_server_")
        loop.set_default_executor(executor)
        log.info("Configured thread pool with 64 workers (crash-on-error enabled)")

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
        parts_search as parts_search_routes,
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
    app.include_router(parts_search_routes.router)
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
        """Shutdown the server (cleanup handled by cleanup_server via atexit)."""
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


# =============================================================================
# Server Entry Point
# =============================================================================

# Register cleanup for any exit path
atexit.register(cleanup_server)


def is_atopile_server_running(port: int) -> bool:
    """Check if an atopile server is already running on the given port."""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except (requests.RequestException, ValueError):
        return False


def run_server(
    port: int,
    workspace_paths: Optional[list[Path]] = None,
    force: bool = False,
) -> None:
    """
    Run the dashboard server.

    Args:
        port: Port to run the server on
        workspace_paths: Workspace paths to scan for projects (defaults to cwd)
        force: Kill existing server on the port if True

    Exit codes:
        0 - Clean shutdown (Ctrl+C or SIGTERM)
        1 - Startup error (port in use, config error)
        2 - Server crash (unhandled exception during operation)
    """
    try:
        _run_server_impl(port, workspace_paths, force)
    except KeyboardInterrupt:
        print("\nShutting down...")
        cleanup_server()
        sys.exit(0)
    except Exception as exc:
        print(f"FATAL SERVER ERROR: {exc}", file=sys.stderr)
        traceback.print_exc()
        cleanup_server(exc)  # Captures exception for telemetry
        sys.exit(2)


def _run_server_impl(
    port: int,
    workspace_paths: Optional[list[Path]],
    force: bool,
) -> None:
    """Server implementation (called by run_server with exception handling)."""
    # Generate types if in dev environment
    repo_root = Path(__file__).resolve().parents[3]
    gen_script = repo_root / "scripts" / "generate_types.py"
    ui_server_dir = repo_root / "src" / "ui-server"
    if gen_script.exists() and ui_server_dir.exists():
        result = subprocess.run([sys.executable, str(gen_script)], cwd=str(repo_root))
        if result.returncode != 0:
            sys.exit(result.returncode)

    # Default to cwd if no workspace paths provided
    if not workspace_paths:
        workspace_paths = [Path.cwd()]

    # Check if port is already in use
    if is_port_in_use(port):
        if force:
            print(f"Stopping existing server on port {port}...")
            if kill_process_on_port(port):
                print("Existing server stopped")
            else:
                print(f"Failed to stop process on port {port}")
                sys.exit(1)
        elif is_atopile_server_running(port):
            print(f"atopile server already running on port {port}")
            print(f"Dashboard available at http://localhost:{port}")
            print("Use --force to restart, or --port to use a different port")
            sys.exit(0)
        else:
            print(f"Port {port} is already in use by another application")
            print("Options:")
            print("  1. Use --force to kill the process: ato serve backend --force")
            print("  2. Use a specific port: ato serve backend --port <PORT>")
            sys.exit(1)

    # Output port early for programmatic discovery (before logging starts)
    # This line is parsed by the VS Code extension and other tools
    print(f"ATOPILE_SERVER_PORT={port}", flush=True)

    # Create and start server
    server = DashboardServer(
        port=port,
        workspace_paths=workspace_paths,
    )

    print(f"Starting dashboard server on http://localhost:{port}")
    print(f"Workspace paths: {', '.join(str(p) for p in workspace_paths)}")
    print("Press Ctrl+C to stop")

    server.start()

    # Handle SIGTERM for clean shutdown (e.g., from process manager)
    def sigterm_handler(_signum, _frame):
        raise KeyboardInterrupt()  # Let the outer handler deal with it

    signal.signal(signal.SIGTERM, sigterm_handler)

    # Keep running until interrupted
    while True:
        time.sleep(1)
