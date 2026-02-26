"""WebSocket connection management and action dispatch for the core server."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import websockets
from websockets.asyncio.server import ServerConnection

from atopile.dataclasses import BuildRequest
from atopile.model.build_queue import BuildQueue, _build_queue
from atopile.model.builds import handle_get_builds, handle_start_build
from atopile.model.projects import handle_get_projects

log = logging.getLogger(__name__)


class CoreSocket:
    """Manages WebSocket connections and dispatches actions."""

    def __init__(self) -> None:
        self._clients: set[ServerConnection] = set()
        self.bind_build_queue(_build_queue)

    # -- Client lifecycle --------------------------------------------------

    async def handle_client(self, ws: ServerConnection) -> None:
        self._clients.add(ws)
        log.info("Core WS client connected (%d total)", len(self._clients))

        try:
            # Send history on connect; active builds will arrive via on_change callbacks
            _, previous = handle_get_builds()
            await ws.send(
                json.dumps({"type": "state", "key": "previousBuilds", "data": previous})
            )

            async for raw in ws:
                msg = json.loads(raw)
                if msg.get("type") == "action":
                    await self._dispatch(ws, msg)

        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)
            log.info("Core WS client disconnected (%d total)", len(self._clients))

    # -- Action dispatch ---------------------------------------------------

    async def _dispatch(self, ws: ServerConnection, msg: dict) -> None:
        match msg.get("action"):
            case "discover_projects":
                paths = [Path(p) for p in msg.get("paths", []) if p]
                result = handle_get_projects(paths)
                await self.broadcast_state("projects", result.model_dump())

            case "start_build":
                request = BuildRequest(
                    project_root=msg.get("projectRoot", ""),
                    targets=msg.get("targets", []),
                )
                try:
                    handle_start_build(request)
                except ValueError as e:
                    log.warning("start_build failed: %s", e)

            case action:
                await ws.send(
                    json.dumps(
                        {
                            "type": "action_result",
                            "action": action,
                            "result": {
                                "success": False,
                                "message": f"Unknown action: {action}",
                            },
                        }
                    )
                )

    # -- Build queue integration -------------------------------------------

    def bind_build_queue(self, build_queue: BuildQueue) -> None:
        """Register as the listener for build queue changes."""
        loop = asyncio.get_running_loop()

        def _on_change(build_id: str, event_type: str) -> None:
            asyncio.run_coroutine_threadsafe(self._push_builds(), loop)

        build_queue.on_change = _on_change
        build_queue.start()

    async def _push_builds(self) -> None:
        current, previous = handle_get_builds()
        await self.broadcast_state("currentBuilds", current)
        await self.broadcast_state("previousBuilds", previous)

    # -- Broadcasting ------------------------------------------------------

    async def broadcast_state(self, key: str, data: Any) -> None:
        msg = json.dumps({"type": "state", "key": key, "data": data})
        dead: list[ServerConnection] = []
        for ws in list(self._clients):
            try:
                await ws.send(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)
