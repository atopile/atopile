import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from atopile.visualizer.project_handler import ProjectHandler
from atopile.utils import get_project_root

# configure logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


watcher = ProjectHandler()

# configure fastapi
@asynccontextmanager
async def lifespan(app: FastAPI):
    watcher.start_watching()
    try:
        yield
    finally:
        watcher.stop_watching()
        watcher.stop_vision_emission()

app = FastAPI(lifespan=lifespan)
static_dir = get_project_root() / "src/visualiser_client/static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/api/")
async def api_root():
    log.info("Hello World")
    return {"message": "Hello World"}

@app.get("/api/view")
async def get_view():
    return watcher.current_view

@app.websocket("/ws/view")
async def websocket_view(websocket: WebSocket):
    await websocket.accept()
    log.info("Websocket accepted")
    await websocket.send_json(watcher.current_view)
    async for vision in watcher.emit_visions():
        await websocket.send_json(vision)

class ElementMovement(BaseModel):
    id: str
    x: int
    y: int

@app.post("/api/view/move")
async def post_move(move: ElementMovement):
    log.info(f"Posted move: {move}")
    watcher.do_move(move.id, move.x, move.y)
