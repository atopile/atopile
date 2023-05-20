import logging
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

import click
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from uvicorn.logging import ColourizedFormatter

from atopile.project.project import Project
from atopile.visualizer.project_handler import ProjectHandler

# configure logging
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.formatter = ColourizedFormatter(fmt="%(levelprefix)s %(message)s", use_colors=None)
logging.root.addHandler(stream_handler)

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
app.mount("/static", StaticFiles(directory="src/visualiser_client/static"), name="static")

@app.get("/api/")
async def api_root():
    log.info("Hello World")
    return {"message": "Hello World"}

@app.get("/api/view")
async def get_view():
    return watcher.current_vision

@app.websocket("/ws/view")
async def websocket_view(websocket: WebSocket):
    await websocket.accept()
    log.info("Websocket accepted")
    await websocket.send_json(watcher.current_vision)
    async for vision in watcher.emit_visions():
        await websocket.send_json(vision)

@app.post("/api/view/move")
async def post_move(move: Dict[Any, Any]):
    log.info(f"Posted move: {move}")
    watcher.do_move(move["id"], move["x"], move["y"])

# configure UI
@click.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.argument("entrypoint", type=str, required=False)
@click.option('--browser/--no-browser', default=False)
def visualize(file: str, entrypoint: str, browser: bool):
    watcher.entrypoint_file = Path(file).resolve().absolute()
    watcher.project = Project.from_path(watcher.entrypoint_file)
    if entrypoint is not None:
        watcher.entrypoint_block = entrypoint
    watcher.rebuild_all()
    if browser:
        webbrowser.open("http://localhost/static/client.html")
    uvicorn.run(app, host="0.0.0.0", port=80)

# let's goooooo
if __name__ == "__main__":
    visualize()
