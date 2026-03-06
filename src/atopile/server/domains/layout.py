"""Layout editor domain service."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import WebSocket

from atopile.layout_server.models import RenderDelta, RenderModel, WsMessage
from atopile.layout_server.pcb_manager import PcbManager
from atopile.model.file_watcher import FileWatcher

log = logging.getLogger(__name__)


class LayoutService:
    """Manage the active PCB and broadcast updates to layout-editor clients."""

    def __init__(self) -> None:
        self._manager: PcbManager | None = None
        self._current_path: Path | None = None
        self._watcher: FileWatcher | None = None
        self._watcher_task: asyncio.Task | None = None
        self._ws_clients: set[WebSocket] = set()

    def load(self, path: Path) -> None:
        resolved = path.resolve()
        log.info("Loading PCB for layout editor: %s", resolved)
        manager = PcbManager()
        manager.load(resolved)
        self._manager = manager
        self._current_path = resolved

    @property
    def manager(self) -> PcbManager:
        if self._manager is None:
            raise RuntimeError("No PCB loaded in layout editor")
        return self._manager

    @property
    def current_path(self) -> Path | None:
        return self._current_path

    @property
    def is_loaded(self) -> bool:
        return self._manager is not None

    async def start_watcher(self) -> None:
        if self._watcher:
            self._watcher.stop()
        if self._watcher_task and not self._watcher_task.done():
            self._watcher_task.cancel()

        if not self._current_path:
            return

        self._watcher = FileWatcher(
            "layout",
            paths=[self._current_path.parent],
            on_change=self._on_file_change,
            glob=self._current_path.name,
            debounce_s=1.0,
        )
        self._watcher_task = asyncio.create_task(self._watcher.run())

    async def add_ws_client(self, ws: WebSocket) -> None:
        await ws.accept()
        self._ws_clients.add(ws)

        if not self.is_loaded:
            return

        model = await asyncio.to_thread(self.manager.get_render_model)
        await ws.send_text(
            WsMessage(type="layout_updated", model=model).model_dump_json()
        )

    def remove_ws_client(self, ws: WebSocket) -> None:
        self._ws_clients.discard(ws)

    async def broadcast(self, message: WsMessage) -> None:
        stale_clients: list[WebSocket] = []
        payload = message.model_dump_json()

        for ws in self._ws_clients:
            try:
                await ws.send_text(payload)
            except Exception:
                stale_clients.append(ws)

        for ws in stale_clients:
            self._ws_clients.discard(ws)

    async def _on_file_change(self, _result: object) -> None:
        if not self._current_path or not self._manager:
            return

        try:
            log.info("PCB file changed on disk, reloading")
            await asyncio.to_thread(self.manager.load, self._current_path)
            model = await asyncio.to_thread(self.manager.get_render_model)
            await self.broadcast(WsMessage(type="layout_updated", model=model))
        except Exception:
            log.exception("Error reloading PCB after file change")

    async def save_and_broadcast(
        self,
        *,
        delta: RenderDelta | None = None,
        action_id: str | None = None,
    ) -> RenderModel | None:
        await asyncio.to_thread(self.manager.save)
        if self._watcher and self._current_path:
            self._watcher.notify_saved(self._current_path)

        if delta is not None:
            await self.broadcast(
                WsMessage(type="layout_delta", delta=delta, action_id=action_id)
            )
            return None

        model = await asyncio.to_thread(self.manager.get_render_model)
        await self.broadcast(
            WsMessage(type="layout_updated", model=model, action_id=action_id)
        )
        return model


layout_service = LayoutService()
