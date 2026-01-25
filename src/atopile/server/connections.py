"""
Connection and event management for the dashboard server.

This module tracks connected WebSocket clients and emits events to them.
The backend no longer owns UI or data state; it only emits notifications.
"""

import asyncio
import logging
import uuid
from typing import Optional

from fastapi import WebSocket

from atopile.dataclasses import ConnectedClient

log = logging.getLogger(__name__)


class ServerConnections:
    """Track WebSocket clients and emit event notifications."""

    def __init__(self) -> None:
        self._clients: dict[str, ConnectedClient] = {}
        self._lock = asyncio.Lock()

    async def connect_client(self, websocket: WebSocket) -> str:
        """Accept a WebSocket connection and return client ID."""
        await websocket.accept()
        client_id = str(uuid.uuid4())[:8]

        async with self._lock:
            self._clients[client_id] = ConnectedClient(
                client_id=client_id, websocket=websocket
            )

        log.info("Client %s connected (total: %d)", client_id, len(self._clients))
        return client_id

    async def disconnect_client(self, client_id: str) -> None:
        """Remove a disconnected client."""
        async with self._lock:
            self._clients.pop(client_id, None)
        log.info("Client %s disconnected (total: %d)", client_id, len(self._clients))

    async def emit_event(self, event_type: str, data: Optional[dict] = None) -> None:
        """Emit an event to all subscribed clients."""
        async with self._lock:
            await self._emit_event_unlocked(event_type, data)

    async def _emit_event_unlocked(
        self, event_type: str, data: Optional[dict] = None
    ) -> None:
        """Emit an event with the lock already held."""
        if not self._clients:
            return

        message = {
            "type": "event",
            "event": event_type,
            "data": data or {},
        }

        dead_clients: list[str] = []
        for client_id, client in self._clients.items():
            if not client.subscribed:
                continue
            try:
                await client.websocket.send_json(message)
            except Exception:
                dead_clients.append(client_id)

        for client_id in dead_clients:
            self._clients.pop(client_id, None)

        if dead_clients:
            log.info("Removed %d dead clients", len(dead_clients))

server_state = ServerConnections()


def get_server_state() -> ServerConnections:
    """FastAPI dependency to get the server connections."""
    return server_state


def reset_server_state() -> ServerConnections:
    """Reset the server connections (used for tests)."""
    global server_state
    server_state = ServerConnections()
    return server_state

