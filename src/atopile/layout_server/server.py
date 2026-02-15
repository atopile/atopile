"""FastAPI application for the PCB Layout Editor."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from atopile.layout_server.models import (
    FootprintSummary,
    MoveFootprintRequest,
    RenderModel,
    RotateFootprintRequest,
    StatusResponse,
    WsMessage,
)
from atopile.layout_server.pcb_manager import PcbManager

STATIC_DIR = Path(__file__).parent / "static"


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def broadcast(self, message: WsMessage) -> None:
        data = message.model_dump()
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                pass


def create_app(pcb_path: Path) -> FastAPI:
    app = FastAPI(title="PCB Layout Editor")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    manager = PcbManager()
    manager.load(pcb_path)

    ws_manager = ConnectionManager()

    async def _broadcast_update() -> None:
        await ws_manager.broadcast(WsMessage(type="layout_updated"))

    @app.get("/api/render-model", response_model=RenderModel)
    async def get_render_model() -> RenderModel:
        return await asyncio.to_thread(manager.get_render_model)

    @app.get(
        "/api/footprints",
        response_model=list[FootprintSummary],
    )
    async def get_footprints() -> list[FootprintSummary]:
        return await asyncio.to_thread(manager.get_footprints)

    @app.post("/api/move-footprint", response_model=StatusResponse)
    async def move_footprint(
        req: MoveFootprintRequest,
    ) -> StatusResponse:
        await asyncio.to_thread(manager.move_footprint, req.uuid, req.x, req.y, req.r)
        await asyncio.to_thread(manager.save)
        await _broadcast_update()
        return StatusResponse(status="ok")

    @app.post("/api/rotate-footprint", response_model=StatusResponse)
    async def rotate_footprint(
        req: RotateFootprintRequest,
    ) -> StatusResponse:
        await asyncio.to_thread(manager.rotate_footprint, req.uuid, req.angle)
        await asyncio.to_thread(manager.save)
        await _broadcast_update()
        return StatusResponse(status="ok")

    @app.post("/api/undo", response_model=StatusResponse)
    async def undo() -> StatusResponse:
        ok = await asyncio.to_thread(manager.undo)
        if ok:
            await asyncio.to_thread(manager.save)
            await _broadcast_update()
            return StatusResponse(status="ok")
        return StatusResponse(status="nothing_to_undo")

    @app.post("/api/redo", response_model=StatusResponse)
    async def redo() -> StatusResponse:
        ok = await asyncio.to_thread(manager.redo)
        if ok:
            await asyncio.to_thread(manager.save)
            await _broadcast_update()
            return StatusResponse(status="ok")
        return StatusResponse(status="nothing_to_redo")

    @app.post("/api/reload", response_model=StatusResponse)
    async def reload() -> StatusResponse:
        await asyncio.to_thread(manager.load, pcb_path)
        await _broadcast_update()
        return StatusResponse(status="ok")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)

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
