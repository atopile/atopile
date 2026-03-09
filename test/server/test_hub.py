"""Test that store updates are broadcast to subscribed webview clients."""

from __future__ import annotations

import asyncio
import json
import socket

import websockets
from ui.hub.hub import Hub
from ui.hub.store import CoreStatus, Store

from ui.hub import store as store_module


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_store_update_broadcasts_to_subscriber():
    """Updating the store broadcasts the new value to subscribed clients."""
    port = _free_port()

    async def run():
        store_module.store = Store()
        hub = Hub(port=port)
        hub_task = asyncio.create_task(hub.run())
        await asyncio.sleep(0.1)

        try:
            async with websockets.connect(f"ws://localhost:{port}/atopile-ui") as ws:
                await ws.send(json.dumps({"type": "subscribe", "keys": ["core"]}))

                # Initial state on subscribe
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
                assert msg == {
                    "type": "state",
                    "key": "core",
                    "data": {"connected": False},
                }

                # Update the store
                store_module.store.core = CoreStatus(connected=True)

                # Should receive the broadcast
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
                assert msg == {
                    "type": "state",
                    "key": "core",
                    "data": {"connected": True},
                }
        finally:
            hub.request_shutdown()
            await hub_task

    asyncio.run(run())
