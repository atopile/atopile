"""
Python WebSocket hub — replaces the Node.js hub.

Acts as a state-store relay between webview clients and the core server.

Webview clients connect via WebSocket to the hub port.
The hub connects as a WebSocket client to the core server's /ws endpoint.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

import websockets

from . import store
from .websocket_core import CoreSocket
from .websocket_webview import WebviewSocket

log = logging.getLogger(__name__)

HUB_READY_MARKER = "ATOPILE_HUB_READY"
CORE_SERVER_PORT_ENV = "ATOPILE_CORE_SERVER_PORT"


class Hub:
    def __init__(self, port: int, core_server_port: Optional[int] = None) -> None:
        self.port = port
        self._shutdown_event = asyncio.Event()

        self._webview_socket = WebviewSocket()
        store.on_change = self._webview_socket.on_store_change

        self._core_socket: Optional[CoreSocket] = None
        if core_server_port is not None:
            self._core_socket = CoreSocket(
                port=core_server_port,
                shutdown_event=self._shutdown_event,
            )

    # -- Lifecycle ---------------------------------------------------------

    async def run(self) -> None:
        """Start the WS server and core-server client, block until shutdown."""
        async with websockets.serve(
            self._webview_socket.handle_client, "localhost", self.port
        ):
            log.info("Hub WS server listening on port %d", self.port)

            # Signal readiness to parent process
            print(HUB_READY_MARKER, flush=True)

            # Start core server relay in the background
            core_task = None
            if self._core_socket is not None:
                core_task = asyncio.create_task(self._core_socket.run())

            # Wait for shutdown signal
            await self._shutdown_event.wait()

            if core_task is not None:
                core_task.cancel()
                try:
                    await core_task
                except asyncio.CancelledError:
                    pass

    def request_shutdown(self) -> None:
        self._shutdown_event.set()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_hub(port: int) -> None:
    """Run the hub (called from ``ato serve hub``)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    raw = os.environ.get(CORE_SERVER_PORT_ENV)
    core_server_port = int(raw) if raw else None

    hub = Hub(port=port, core_server_port=core_server_port)

    loop = asyncio.new_event_loop()

    def _signal_handler() -> None:
        hub.request_shutdown()

    if sys.platform != "win32":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _signal_handler)

    try:
        loop.run_until_complete(hub.run())
    finally:
        loop.close()
