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
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import websockets

from atopile.dataclasses import AppContext
from atopile.model.build_queue import _build_queue
from atopile.model.sqlite import BuildHistory, Logs
from atopile.server.websocket import CoreSocket

log = logging.getLogger(__name__)


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

    def _cleanup(self, exc: BaseException | None = None) -> None:
        """
        Cleanup server resources before exit.

        All steps are best-effort - failures don't prevent other cleanup.
        """
        try:
            _build_queue.stop()
        except Exception:
            pass

        try:
            from atopile.logging import BuildLogger

            BuildLogger.close_all()
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
        BuildHistory.init_db()
        Logs.init_db()

        core = CoreSocket()

        async with websockets.serve(
            core.handle_client,
            "127.0.0.1",
            self.port,
        ):
            print("ATOPILE_SERVER_READY", flush=True)
            log.info("Core server ready")
            await asyncio.Future()  # run forever
