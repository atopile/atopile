import asyncio
import logging
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List

import click
import uvicorn
import watchfiles
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from uvicorn.logging import ColourizedFormatter

from atopile.model.model import Model
from atopile.parser.parser import Builder
from atopile.project.project import Project
from atopile.visualizer.visualizer import build_dict

# configure logging
log = logging.Logger(__name__, level=logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.formatter = ColourizedFormatter(fmt="%(levelprefix)s %(message)s", use_colors=None)
log.addHandler(stream_handler)

class AtoWatcher:
    def __init__(self):
        self.project: Project = None
        self.entrypoint_file = None
        self._entrypoint_block = None

        self._model: Model = None
        self._visualizer_dict = None

        self._task: asyncio.Task = None
        self._watchers: List[asyncio.Queue] = []

    @property
    def entrypoint_block(self):
        if self._entrypoint_block is None:
            return str(self.project.standardise_import_path(self.entrypoint_file))
        return self._entrypoint_block

    @entrypoint_block.setter
    def entrypoint_block(self, value):
        self._entrypoint_block = value

    @property
    def visualizer_dict(self):
        if self._visualizer_dict is None:
            self.rebuild()
        return self._visualizer_dict

    def rebuild(self):
        log.info("Rebuilding model")
        self._model = Builder(self.project).build(self.entrypoint_file)
        self._visualizer_dict = build_dict(self._model, self.entrypoint_block)

    async def _watch_files(self):
        try:
            async for changes in watchfiles.awatch(self.project.root):
                log.info("Changes detected in project directory.")
                # figure out what source files have been updated
                changed_src_files = []
                for _, file in changes:
                    std_path = self.project.standardise_import_path(Path(file))
                    if std_path in self._model.src_files:
                        changed_src_files.append(std_path)

                if changed_src_files:
                    self.rebuild()
                    for queue in self._watchers:
                        await queue.put(self._visualizer_dict)
        except Exception as ex:
            log.exception(str(ex))
            raise

    def start_watching(self):
        self._task = asyncio.create_task(self._watch_files())

    def stop_watching(self):
        self._task.cancel()

    async def emit_visions(self) -> dict:
        queue = asyncio.Queue()
        self._watchers.append(queue)
        try:
            while True:
                visions = await queue.get()
                if isinstance(visions, asyncio.CancelledError) or visions == asyncio.CancelledError:
                    raise visions
                yield visions
        finally:
            self._watchers.remove(queue)

    def stop_vision_emission(self):
        for queue in self._watchers:
            queue.put(asyncio.CancelledError)

watcher = AtoWatcher()

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

@app.get("/api/graph")
async def get_graph():
    return watcher.visualizer_dict

@app.websocket("/ws/graph")
async def websocket_graph(websocket: WebSocket):
    await websocket.accept()
    log.info("Websocket accepted")
    await websocket.send_json(watcher.visualizer_dict)
    async for vision in watcher.emit_visions():
        await websocket.send_json(vision)

# configure UI
@click.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.argument("entrypoint", type=str, required=False)
def visualize(file: str, entrypoint: str):
    watcher.entrypoint_file = Path(file).resolve().absolute()
    watcher.project = Project.from_path(watcher.entrypoint_file)
    if entrypoint is not None:
        watcher.entrypoint_block = entrypoint
    webbrowser.open("http://localhost/static/client.html")
    uvicorn.run(app, host="0.0.0.0", port=80)

# let's goooooo
if __name__ == "__main__":
    visualize()
