"""FastAPI application for the PCB Layout Editor."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from atopile.layout_server.models import (
    ActionRequest,
    FootprintSummary,
    RenderModel,
    StatusResponse,
    WsMessage,
)
from atopile.layout_server.pcb_manager import PcbManager

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def broadcast(self, message: WsMessage) -> None:
        data = message.model_dump(exclude_none=True)
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                pass


async def _watch_file(
    pcb_path: Path, manager: PcbManager, ws_manager: ConnectionManager
) -> None:
    """Watch pcb file for external changes and reload."""
    import watchfiles

    log.info("File watcher started for %s", pcb_path)
    async for _changes in watchfiles.awatch(pcb_path):
        if manager.was_recently_saved():
            log.debug("Ignoring self-triggered file change")
            continue
        try:
            log.info("PCB file changed on disk, reloading")
            await asyncio.to_thread(manager.load, pcb_path)
            model = await asyncio.to_thread(manager.get_render_model)
            await ws_manager.broadcast(WsMessage(type="layout_updated", model=model))
        except Exception:
            log.exception("Error reloading PCB after file change")


def create_app(pcb_path: Path) -> FastAPI:
    manager = PcbManager()
    manager.load(pcb_path)
    ws_manager = ConnectionManager()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = asyncio.create_task(_watch_file(pcb_path, manager, ws_manager))
        yield
        task.cancel()

    app = FastAPI(title="PCB Layout Editor", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/render-model", response_model=RenderModel)
    async def get_render_model() -> RenderModel:
        return await asyncio.to_thread(manager.get_render_model)

    @app.get(
        "/api/footprints",
        response_model=list[FootprintSummary],
    )
    async def get_footprints() -> list[FootprintSummary]:
        return await asyncio.to_thread(manager.get_footprints)

    async def _save_and_broadcast() -> RenderModel:
        await asyncio.to_thread(manager.save)
        model = await asyncio.to_thread(manager.get_render_model)
        await ws_manager.broadcast(WsMessage(type="layout_updated", model=model))
        return model

    @app.post("/api/execute-action", response_model=StatusResponse)
    async def execute_action(req: ActionRequest) -> StatusResponse:
        try:
            ok = await asyncio.to_thread(manager.dispatch_action, req.type, req.details)
        except TypeError as e:
            return StatusResponse(status=f"invalid_details:{e}")
        if not ok:
            return StatusResponse(status=f"unknown_action:{req.type}")
        model = await _save_and_broadcast()
        return StatusResponse(status="ok", model=model)

    @app.post("/api/undo", response_model=StatusResponse)
    async def undo() -> StatusResponse:
        ok = await asyncio.to_thread(manager.undo)
        if ok:
            model = await _save_and_broadcast()
            return StatusResponse(status="ok", model=model)
        return StatusResponse(status="nothing_to_undo")

    @app.post("/api/redo", response_model=StatusResponse)
    async def redo() -> StatusResponse:
        ok = await asyncio.to_thread(manager.redo)
        if ok:
            model = await _save_and_broadcast()
            return StatusResponse(status="ok", model=model)
        return StatusResponse(status="nothing_to_redo")

    @app.post("/api/reload", response_model=StatusResponse)
    async def reload() -> StatusResponse:
        await asyncio.to_thread(manager.load, pcb_path)
        model = await asyncio.to_thread(manager.get_render_model)
        await ws_manager.broadcast(WsMessage(type="layout_updated", model=model))
        return StatusResponse(status="ok", model=model)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)

    # --- Static files ---

    @app.get("/")
    async def index():
        index_path = STATIC_DIR / "index.html"
        return HTMLResponse(index_path.read_text())

    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

    return app
