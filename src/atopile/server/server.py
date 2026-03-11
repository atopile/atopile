"""
atopile core server.

Provides a WebSocket endpoint for build data. The React frontend is served
directly by VS Code webview for better IDE integration.

Usage:
    python -m atopile.server --port PORT [--workspace PATH]

Exception Contract:
    - Build exceptions run in subprocesses and mark builds as FAILED
    - Server exceptions crash the entire server process
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
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import uvicorn
import websockets

from atopile.dataclasses import AppContext
from atopile.layout_server.__main__ import create_app_for_service
from atopile.logging import get_logger
from atopile.model.build_queue import _build_queue
from atopile.model.sqlite import BuildHistory, Logs
from atopile.server.domains.layout import layout_service
from atopile.server.ui.websocket import CoreSocket

log = get_logger(__name__)


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
        force: bool = False,
        ctx: Optional[AppContext] = None,
    ):
        self.port = port
        self.force = force
        self.ctx = ctx or AppContext()
        self._layout_http_server: _UvicornServerNoSignals | None = None
        self._layout_http_task: asyncio.Task[None] | None = None

    def _cleanup(self, exc: BaseException | None = None) -> None:
        """
        Cleanup server resources before exit.

        All steps are best-effort - failures don't prevent other cleanup.
        """
        try:
            if self._layout_http_server:
                self._layout_http_server.should_exit = True
            if self._layout_http_task:
                self._layout_http_task.cancel()
        except Exception:
            pass

        try:
            _build_queue.stop()
        except Exception:
            pass

        try:
            from atopile.logging import AtoLogger

            AtoLogger.close_all()
        except Exception:
            pass

        try:
            from atopile import telemetry

            if exc:
                telemetry.capture_exception(exc)
            telemetry._flush_telemetry_on_exit()
        except Exception:
            pass

        try:
            logging.shutdown()
        except Exception:
            pass

    def _crash_on_asyncio_exception(
        self, loop: asyncio.AbstractEventLoop, context: dict
    ) -> None:
        """
        Handle uncaught exceptions in asyncio tasks by crashing the server.

        This ensures background task failures are visible instead of being
        silently logged and ignored.
        """
        exc = context.get("exception")
        msg = context.get("message", "Unknown asyncio error")

        log.critical("Uncaught exception in asyncio task: %s", msg)
        fatal_msg = (
            f"Asyncio task crashed: {msg}" if exc else f"Asyncio task error: {msg}"
        )
        log.critical("FATAL SERVER ERROR: %s", fatal_msg)
        if exc:
            log.critical(
                "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            )

        self._cleanup(exc)
        os._exit(2)

    def _log_thread_exception(self, args: threading.ExceptHookArgs) -> None:
        """Log uncaught background-thread exceptions through the core logger."""
        if args.exc_type is KeyboardInterrupt:
            return
        thread_name = args.thread.name if args.thread else "unknown"
        log.critical(
            "Uncaught exception in thread %s",
            thread_name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    async def _start_layout_server(self) -> None:
        port = int(os.getenv("ATOPILE_LAYOUT_SERVER_PORT", "0"))
        if port <= 0:
            return

        if is_port_in_use(port):
            if self.force:
                if not kill_process_on_port(port):
                    raise RuntimeError(f"Failed to stop process on layout port {port}")
            else:
                raise RuntimeError(f"Layout server port {port} is already in use")

        self._layout_http_server = _UvicornServerNoSignals(
            uvicorn.Config(
                create_app_for_service(layout_service),
                host="127.0.0.1",
                port=port,
                log_level="warning",
                access_log=False,
            )
        )
        self._layout_http_task = asyncio.create_task(self._layout_http_server.serve())

        deadline = time.monotonic() + 5
        while not self._layout_http_server.started:
            if self._layout_http_task.done():
                if self._layout_http_task.cancelled():
                    raise RuntimeError("Layout server startup was cancelled")
                exc = self._layout_http_task.exception()
                if exc:
                    raise RuntimeError("Layout server exited during startup") from exc
                raise RuntimeError("Layout server exited before startup")
            if time.monotonic() >= deadline:
                self._layout_http_server.should_exit = True
                raise RuntimeError("Layout server did not start within 5 seconds")
            await asyncio.sleep(0.05)

        log.info("Layout server ready on http://127.0.0.1:%s", port)

    def run(self) -> None:
        """Start the server and block until interrupted."""
        signal.signal(
            signal.SIGTERM,
            lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()),
        )

        try:
            if is_port_in_use(self.port):
                if self.force:
                    log.info(
                        "Stopping existing server on port %s...",
                        self.port,
                    )
                    if not kill_process_on_port(self.port):
                        log.error(
                            "Failed to stop process on port %s",
                            self.port,
                        )
                        sys.exit(1)
                    log.info("Existing server stopped")
                else:
                    log.error("Port %s is already in use", self.port)
                    log.error("Use --force to kill the process: ato serve core --force")
                    sys.exit(1)

            log.info("Starting core server on ws://localhost:%s", self.port)
            asyncio.run(self._serve_forever())

        except KeyboardInterrupt:
            log.info("Shutting down...")
            self._cleanup()
            sys.exit(0)
        except Exception as exc:
            log.exception("FATAL SERVER ERROR")
            self._cleanup(exc)
            sys.exit(2)

    async def _serve_forever(self) -> None:
        """Run websocket server until process termination."""
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(self._crash_on_asyncio_exception)
        loop.set_default_executor(
            ThreadPoolExecutor(max_workers=64, thread_name_prefix="ato_server_")
        )
        threading.excepthook = self._log_thread_exception
        BuildHistory.init_db()
        Logs.init_db()

        await self._start_layout_server()
        core = CoreSocket()

        async with websockets.serve(
            core.handle_client,
            "127.0.0.1",
            self.port,
        ):
            print("ATOPILE_SERVER_READY", flush=True)
            log.info("Core server ready")
            await asyncio.Future()  # run forever


class _UvicornServerNoSignals(uvicorn.Server):
    def install_signal_handlers(self) -> None:
        return
