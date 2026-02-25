"""WebSocket client that connects to the core server."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from typing import Any

import websockets

from .store import CoreStatus, store

log = logging.getLogger(__name__)


class CoreSocket:
    """Maintains a reconnecting WebSocket connection to the core server."""

    def __init__(
        self,
        *,
        port: int,
        on_connected: Any = None,
    ) -> None:
        self._port = port
        self._on_connected = on_connected
        self._ws: websockets.WebSocketClientProtocol | None = None

    async def send_action(self, msg: dict) -> None:
        """Forward an action message to the core server."""
        if self._ws is not None:
            try:
                await self._ws.send(json.dumps(msg))
            except Exception:
                log.exception("Failed to send action to core server")

    async def run(self) -> None:
        """Connect to core server with exponential backoff reconnect.

        Cancel the task to stop.
        """
        delay = 1.0
        max_delay = 10.0
        url = f"ws://localhost:{self._port}/atopile-core"

        while True:
            try:
                log.info("Connecting to core server at %s", url)
                async with websockets.connect(url) as ws:
                    self._ws = ws
                    log.info("Connected to core server")
                    store.core_status = CoreStatus(connected=True)
                    delay = 1.0
                    if self._on_connected is not None:
                        await self._on_connected()
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            log.warning("Failed to parse core server message")
                            continue
                        if msg.get("type") == "state":
                            key = msg.get("key")
                            data = msg.get("data", {})
                            value = tuple(data.get(key, []))
                            store.project_state = replace(
                                store.project_state, **{key: value}
                            )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.info("Core server connection lost: %s", exc)
            finally:
                self._ws = None
                store.core_status = CoreStatus(connected=False)

            log.info("Reconnecting to core server in %.1fs", delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)
