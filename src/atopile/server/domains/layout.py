"""Layout editor domain — manages the active PCB for the layout editor."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import WebSocket

from atopile.layout_server.models import RenderModel, WsMessage
from atopile.layout_server.pcb_manager import PcbManager

log = logging.getLogger(__name__)


class LayoutService:
    """Manages a single active PcbManager instance for the layout editor."""

    def __init__(self) -> None:
        self._manager: PcbManager | None = None
        self._current_path: Path | None = None
        self._ws_clients: list[WebSocket] = []
        self._watcher_task: asyncio.Task | None = None

    def load(self, path: Path) -> None:
        """Load (or replace) the active PCB file.  Sync-only — call
        ``start_watcher()`` afterwards from an async context."""
        resolved = path.resolve()
        log.info("Loading PCB for layout editor: %s", resolved)
        mgr = PcbManager()
        mgr.load(resolved)
        self._manager = mgr
        self._current_path = resolved

    @property
    def manager(self) -> PcbManager:
        """Return the active PcbManager, or raise if nothing is loaded."""
        if self._manager is None:
            raise RuntimeError("No PCB loaded in layout editor")
        return self._manager

    @property
    def current_path(self) -> Path | None:
        return self._current_path

    @property
    def is_loaded(self) -> bool:
        return self._manager is not None

    # --- WebSocket client management ---

    async def add_ws_client(self, ws: WebSocket) -> None:
        await ws.accept()
        self._ws_clients.append(ws)

    def remove_ws_client(self, ws: WebSocket) -> None:
        try:
            self._ws_clients.remove(ws)
        except ValueError:
            pass

    async def broadcast(self, msg: WsMessage) -> None:
        data = msg.model_dump(exclude_none=True)
        for ws in list(self._ws_clients):
            try:
                await ws.send_json(data)
            except Exception:
                pass

    # --- File watcher ---

    async def start_watcher(self) -> None:
        """(Re)start the file watcher.  Must be called from the event loop
        thread — typically right after ``await to_thread(load, ...)``."""
        if self._watcher_task and not self._watcher_task.done():
            self._watcher_task.cancel()
        self._watcher_task = asyncio.create_task(self._watch_file())

    async def _watch_file(self) -> None:
        if not self._current_path:
            return
        import watchfiles

        log.info("Layout file watcher started for %s", self._current_path)
        async for _changes in watchfiles.awatch(self._current_path):
            if self._manager and self._manager.was_recently_saved():
                log.debug("Ignoring self-triggered file change")
                continue
            try:
                log.info("PCB file changed on disk, reloading")
                await asyncio.to_thread(self.manager.load, self._current_path)
                model = await asyncio.to_thread(self.manager.get_render_model)
                await self.broadcast(WsMessage(type="layout_updated", model=model))
            except Exception:
                log.exception("Error reloading PCB after file change")

    # --- Save and broadcast helper ---

    async def save_and_broadcast(self) -> RenderModel:
        """Save the PCB to disk and broadcast the updated model to all WS clients."""
        await asyncio.to_thread(self.manager.save)
        model = await asyncio.to_thread(self.manager.get_render_model)
        await self.broadcast(WsMessage(type="layout_updated", model=model))
        return model


layout_service = LayoutService()
