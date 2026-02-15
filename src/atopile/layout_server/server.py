"""FastAPI application for the PCB Layout Editor."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from atopile.layout_server.pcb_manager import PcbManager

STATIC_DIR = Path(__file__).parent / "static"


class MoveFootprintRequest(BaseModel):
    uuid: str
    x: float
    y: float
    r: float | None = None


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
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

    @app.get("/api/render-model")
    async def get_render_model():
        return await asyncio.to_thread(manager.get_render_model)

    @app.get("/api/footprints")
    async def get_footprints():
        return await asyncio.to_thread(manager.get_footprints)

    @app.post("/api/move-footprint")
    async def move_footprint(req: MoveFootprintRequest):
        await asyncio.to_thread(manager.move_footprint, req.uuid, req.x, req.y, req.r)
        await asyncio.to_thread(manager.save)
        await ws_manager.broadcast({"type": "layout_updated"})
        return {"status": "ok"}

    @app.post("/api/reload")
    async def reload():
        await asyncio.to_thread(manager.load, pcb_path)
        await ws_manager.broadcast({"type": "layout_updated"})
        return {"status": "ok"}

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

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    return app
