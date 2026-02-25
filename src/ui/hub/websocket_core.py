"""WebSocket client that connects to the core server."""

from __future__ import annotations

import asyncio
import logging

import websockets

from .store import CoreStatus, store

log = logging.getLogger(__name__)


class CoreSocket:
    """Maintains a reconnecting WebSocket connection to the core server."""

    def __init__(self, *, port: int, shutdown_event: asyncio.Event) -> None:
        self._port = port
        self._shutdown_event = shutdown_event

    async def run(self) -> None:
        """Connect to core server with exponential backoff reconnect."""
        delay = 1.0
        max_delay = 10.0
        url = f"ws://localhost:{self._port}/atopile-core"

        while not self._shutdown_event.is_set():
            try:
                log.info("Connecting to core server at %s", url)
                async with websockets.connect(url) as ws:
                    log.info("Connected to core server")
                    store.core = CoreStatus(connected=True)
                    delay = 1.0
                    async for raw in ws:
                        pass  # No messages handled yet
            except Exception as exc:
                log.info("Core server connection lost: %s", exc)
                store.core = CoreStatus(connected=False)
            finally:
                store.core = CoreStatus(connected=False)

            if self._shutdown_event.is_set():
                break

            log.info("Reconnecting to core server in %.1fs", delay)
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=delay)
                break
            except asyncio.TimeoutError:
                pass
            delay = min(delay * 2, max_delay)
