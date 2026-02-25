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
from dataclasses import replace
from typing import Any, Optional

import websockets

from . import store
from .websocket_core import CoreSocket
from .websocket_webview import WebviewSocket

log = logging.getLogger(__name__)

HUB_READY_MARKER = "ATOPILE_HUB_READY"
CORE_SERVER_PORT_ENV = "ATOPILE_CORE_SERVER_PORT"


class Hub:
    def __init__(
        self,
        port: int,
        core_server_port: Optional[int] = None,
        workspace_folders: Optional[list[str]] = None,
    ) -> None:
        self.port = port
        self._workspace_folders = workspace_folders or []
        self._shutdown_event = asyncio.Event()

        self._webview_socket = WebviewSocket()
        self._webview_socket.on_action = self._handle_action
        store.on_change = self._on_store_change

        self._core_socket: Optional[CoreSocket] = None
        if core_server_port is not None:
            self._core_socket = CoreSocket(
                port=core_server_port,
                on_connected=self._on_core_connected,
            )

    # -- Store change handling ---------------------------------------------

    async def _on_store_change(self, key: str, value: Any) -> None:
        """Called when any store field changes."""
        await self._webview_socket.on_store_change(key, value)

    # -- Core connection handling ------------------------------------------

    async def _on_core_connected(self) -> None:
        """Called when the core server WebSocket connects."""
        # Ask core to discover projects using our workspace paths
        await self._core_socket.send_action(
            {
                "type": "action",
                "action": "discover_projects",
                "paths": self._workspace_folders,
            }
        )

    # -- Action routing ----------------------------------------------------

    async def _handle_action(self, msg: dict) -> None:
        """Route an action from a webview client."""
        s = store.store
        match msg.get("action"):
            case "select_project":
                s.project_state = replace(
                    s.project_state,
                    selected_project=msg.get("projectRoot"),
                    selected_target=None,
                )
                return
            case "select_target":
                s.project_state = replace(
                    s.project_state, selected_target=msg.get("target")
                )
                return
            case "discover_projects":
                msg = {**msg, "paths": self._workspace_folders}
        # Everything else goes to the core server
        if self._core_socket is not None:
            await self._core_socket.send_action(msg)

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

    workspace_folders = [
        p for p in os.environ.get("ATOPILE_WORKSPACE_FOLDERS", "").split(":") if p
    ]

    hub = Hub(
        port=port,
        core_server_port=core_server_port,
        workspace_folders=workspace_folders,
    )

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
