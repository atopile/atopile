"""
Python WebSocket hub — replaces the Node.js hub.

Acts as a state-store relay between webview clients and the core server.

Webview clients connect via WebSocket to the hub port.
The hub connects as a WebSocket client to the core server's /ws endpoint.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
from typing import Any, Optional

import websockets
from websockets.asyncio.server import ServerConnection

log = logging.getLogger(__name__)

HUB_READY_MARKER = "ATOPILE_HUB_READY"
CORE_SERVER_PORT_ENV = "ATOPILE_CORE_SERVER_PORT"


# ---------------------------------------------------------------------------
# State store
# ---------------------------------------------------------------------------


class StateStore:
    """In-memory shared UI state (dict with patch/replace)."""

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}

    def get(self) -> dict[str, Any]:
        return dict(self._state)

    def patch(self, partial: dict[str, Any]) -> None:
        self._state.update(partial)

    def replace(self, full: dict[str, Any]) -> None:
        self._state = dict(full)


# ---------------------------------------------------------------------------
# Hub
# ---------------------------------------------------------------------------


class Hub:
    def __init__(self, port: int, core_server_port: Optional[int] = None) -> None:
        self.port = port
        self.core_server_port = core_server_port
        self.store = StateStore()
        self._clients: set[ServerConnection] = set()
        self._core_ws: Optional[Any] = None
        self._shutdown_event = asyncio.Event()

    # -- WebSocket server (webview clients) --------------------------------

    async def _handle_client(self, ws: ServerConnection) -> None:
        if ws.request.path != "/atopile-ui":
            await ws.close(4000, "unknown path")
            return
        self._clients.add(ws)
        log.info("Client connected (%d total)", len(self._clients))
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    await self._on_client_message(ws, msg)
                except json.JSONDecodeError:
                    log.warning("Failed to parse client message")
        finally:
            self._clients.discard(ws)
            log.info("Client disconnected (%d total)", len(self._clients))

    async def _on_client_message(self, ws: ServerConnection, msg: dict) -> None:
        msg_type = msg.get("type")
        if msg_type == "subscribe":
            await ws.send(json.dumps({"type": "state", "data": self.store.get()}))
        elif msg_type == "action":
            if self._core_ws is not None:
                try:
                    await self._core_ws.send(
                        json.dumps(
                            {
                                "type": "action",
                                "action": msg.get("action", ""),
                                "payload": msg.get("payload"),
                            }
                        )
                    )
                except Exception:
                    log.warning("Failed to forward action to core server")
        elif msg_type == "patch":
            data = msg.get("data")
            if isinstance(data, dict):
                self.store.patch(data)
                await self._broadcast({"type": "state", "data": self.store.get()})

    # -- WebSocket client (core server) ------------------------------------

    async def _core_server_loop(self) -> None:
        """Connect to core server with exponential backoff reconnect."""
        if self.core_server_port is None:
            return

        delay = 1.0
        max_delay = 10.0
        url = f"ws://localhost:{self.core_server_port}/atopile-core"

        while not self._shutdown_event.is_set():
            try:
                log.info("Connecting to core server at %s", url)
                async with websockets.connect(url) as ws:
                    self._core_ws = ws
                    log.info("Connected to core server")
                    delay = 1.0  # reset backoff
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                            await self._on_core_server_message(msg)
                        except json.JSONDecodeError:
                            log.warning("Failed to parse core server message")
            except Exception as exc:
                log.info("Core server connection lost: %s", exc)
                self._core_ws = None
            finally:
                self._core_ws = None

            if self._shutdown_event.is_set():
                break

            log.info("Reconnecting to core server in %.1fs", delay)
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=delay)
                break  # shutdown requested during wait
            except asyncio.TimeoutError:
                pass
            delay = min(delay * 2, max_delay)

    async def _on_core_server_message(self, msg: dict) -> None:
        msg_type = msg.get("type")
        if msg_type == "state":
            data = msg.get("data")
            if isinstance(data, dict):
                self.store.replace(data)
                await self._broadcast({"type": "state", "data": self.store.get()})
        elif msg_type == "event":
            await self._broadcast(
                {
                    "type": "event",
                    "event": msg.get("event", ""),
                    "data": msg.get("data"),
                }
            )
        elif msg_type == "action_result":
            await self._broadcast(
                {
                    "type": "action_result",
                    "action": msg.get("action", ""),
                    "result": msg.get("result"),
                }
            )

    # -- Broadcasting ------------------------------------------------------

    async def _broadcast(self, msg: dict) -> None:
        payload = json.dumps(msg)
        dead: list[ServerConnection] = []
        for client in list(self._clients):
            try:
                await client.send(payload)
            except Exception:
                dead.append(client)
        for client in dead:
            self._clients.discard(client)

    # -- Lifecycle ---------------------------------------------------------

    async def run(self) -> None:
        """Start the WS server and core-server client, block until shutdown."""
        async with websockets.serve(self._handle_client, "localhost", self.port):
            log.info("Hub WS server listening on port %d", self.port)

            # Signal readiness to parent process
            print(HUB_READY_MARKER, flush=True)

            # Start core server relay in the background
            core_task = asyncio.create_task(self._core_server_loop())

            # Wait for shutdown signal
            await self._shutdown_event.wait()

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
