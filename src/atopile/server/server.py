"""
atopile core server.

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
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
from typing import Optional

import requests
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from atopile.dataclasses import AppContext
from atopile.model.build_queue import _build_queue
from atopile.model.sqlite import BuildHistory

log = logging.getLogger(__name__)


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
        log.critical(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        )

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
    ato_source: Optional[str] = None,
    ato_local_path: Optional[str] = None,
    ato_binary_path: Optional[str] = None,
    ato_from_branch: Optional[str] = None,
    ato_from_spec: Optional[str] = None,
) -> FastAPI:
    """
    Create the FastAPI application for the core server.

    Exception Handling:
        - Unhandled exceptions in routes → server crashes (not HTTP 500)
        - Unhandled exceptions in background tasks → server crashes
        - HTTPException → proper HTTP error response (intentional)
    """
    app = FastAPI(title="atopile Core Server")

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
        ato_source=ato_source,
        ato_local_path=ato_local_path,
        ato_binary_path=ato_binary_path,
        ato_from_branch=ato_from_branch,
        ato_from_spec=ato_from_spec,
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

    # Health check endpoint for extension to verify server is running
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {"status": "ok"}

    @app.websocket("/atopile-core")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for the VS Code extension hub."""
        await websocket.accept()
        # Send initial state
        await websocket.send_json({"type": "state", "data": {}})
        try:
            while True:
                msg = await websocket.receive_json()
                # Echo back action_result for any action
                if msg.get("type") == "action":
                    await websocket.send_json(
                        {
                            "type": "action_result",
                            "action": msg.get("action", ""),
                            "result": {"success": True},
                        }
                    )
        except WebSocketDisconnect:
            pass

    return app


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


class CoreServer:
    """Manages the core server lifecycle."""

    def __init__(
        self,
        port: int,
        ato_source: Optional[str] = None,
        ato_local_path: Optional[str] = None,
        ato_binary_path: Optional[str] = None,
        ato_from_branch: Optional[str] = None,
        ato_from_spec: Optional[str] = None,
    ):
        self.port = port
        self.app = create_app(
            ato_source=ato_source,
            ato_local_path=ato_local_path,
            ato_binary_path=ato_binary_path,
            ato_from_branch=ato_from_branch,
            ato_from_spec=ato_from_spec,
        )
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        """Get the server URL."""
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
        else:
            raise RuntimeError("Core server failed to start within 5 seconds")

    def shutdown(self) -> None:
        """Shutdown the server (cleanup handled by cleanup_server via atexit)."""
        if self._server:
            self._server.should_exit = True
            if self._thread:
                self._thread.join(timeout=2.0)


# =============================================================================
# Server Entry Point
# =============================================================================


def is_atopile_server_running(port: int) -> bool:
    """Check if an atopile server is already running on the given port."""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except (requests.RequestException, ValueError):
        return False


def run_server(
    port: int,
    force: bool = False,
    ato_source: Optional[str] = None,
    ato_binary_path: Optional[str] = None,
    ato_local_path: Optional[str] = None,
    ato_from_branch: Optional[str] = None,
    ato_from_spec: Optional[str] = None,
) -> None:
    """
    Run the core server.

    Args:
        port: Port to run the server on
        force: Kill existing server on the port if True
        ato_source: Source of the atopile binary
            ('explicit-path', 'from-setting', 'default')
        ato_binary_path: Actual resolved path to the ato binary
        ato_local_path: Local path to display in the UI (for explicit-path mode)
        ato_from_branch: Git branch name when installed from git via uv
        ato_from_spec: The pip/uv spec used (for from-setting mode)

    Exit codes:
        0 - Clean shutdown (Ctrl+C or SIGTERM)
        1 - Startup error (port in use, config error)
        2 - Server crash (unhandled exception during operation)
    """
    try:
        _run_server_impl(
            port,
            force,
            ato_source=ato_source,
            ato_binary_path=ato_binary_path,
            ato_local_path=ato_local_path,
            ato_from_branch=ato_from_branch,
            ato_from_spec=ato_from_spec,
        )
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
    force: bool,
    ato_source: Optional[str] = None,
    ato_binary_path: Optional[str] = None,
    ato_local_path: Optional[str] = None,
    ato_from_branch: Optional[str] = None,
    ato_from_spec: Optional[str] = None,
) -> None:
    """Server implementation (called by run_server with exception handling)."""
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
            print(f"Core server already running on port {port}")
            print(f"Server available at http://localhost:{port}")
            print("Use --force to restart")
            sys.exit(0)
        else:
            print(f"Port {port} is already in use by another application")
            print("Use --force to kill the process: ato serve core --force")
            sys.exit(1)

    # Create and start server
    server = CoreServer(
        port=port,
        ato_source=ato_source,
        ato_local_path=ato_local_path,
        ato_binary_path=ato_binary_path,
        ato_from_branch=ato_from_branch,
        ato_from_spec=ato_from_spec,
    )

    print(f"Starting core server on http://localhost:{port}")

    server.start()

    # Output ready marker AFTER server is listening — this is parsed by the
    # VS Code extension to know the server is ready.
    print("ATOPILE_SERVER_READY", flush=True)

    # Handle SIGTERM for clean shutdown (e.g., from process manager)
    def sigterm_handler(_signum, _frame):
        raise KeyboardInterrupt()  # Let the outer handler deal with it

    signal.signal(signal.SIGTERM, sigterm_handler)

    # Keep running until interrupted
    while True:
        time.sleep(1)
