"""WebSocket server for webview clients."""

from __future__ import annotations

import json
import logging
from typing import Any

from websockets.asyncio.server import ServerConnection

from .store import store

log = logging.getLogger(__name__)


class WebviewSocket:
    """Manages WebSocket connections from webview clients.

    Clients subscribe to specific store keys. When a key changes,
    only clients subscribed to that key receive the full updated value.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[ServerConnection, set[str]] = {}
        self.on_action: Any = None  # async callback for action messages

    async def handle_client(self, ws: ServerConnection) -> None:
        """WebSocket handler passed to ``websockets.serve``."""
        if ws.request.path != "/atopile-ui":
            await ws.close(4000, "unknown path")
            return
        self._subscriptions[ws] = set()
        log.info("Client connected (%d total)", len(self._subscriptions))
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    await self._on_message(ws, msg)
                except json.JSONDecodeError:
                    log.warning("Failed to parse client message")
        finally:
            del self._subscriptions[ws]
            log.info("Client disconnected (%d total)", len(self._subscriptions))

    async def _on_message(self, ws: ServerConnection, msg: dict) -> None:
        match msg.get("type"):
            case "subscribe":
                keys = msg.get("keys")
                if isinstance(keys, list):
                    self._subscriptions[ws] = set(keys)
                    for key in keys:
                        try:
                            value = store.get(key)
                            await self._send(
                                ws, {"type": "state", "key": key, "data": value}
                            )
                        except AttributeError:
                            log.warning("Client subscribed to unknown key: %s", key)
            case "action":
                if self.on_action:
                    await self.on_action(msg)

    async def on_store_change(self, key: str, value: Any) -> None:
        """Called when a store field changes. Sends to subscribed clients."""
        msg = {"type": "state", "key": key, "data": value}
        payload = json.dumps(msg)
        dead: list[ServerConnection] = []
        for ws, keys in list(self._subscriptions.items()):
            if key not in keys:
                continue
            try:
                await ws.send(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            del self._subscriptions[ws]

    async def _send(self, ws: ServerConnection, msg: dict) -> None:
        await ws.send(json.dumps(msg))
