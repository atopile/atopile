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


project_handler = ProjectHandler()

# TODO: monitor project live
# configure fastapi
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     watcher.monitor_project()
#     try:
#         yield
#     finally:
#         watcher.teardown()

# app = FastAPI(lifespan=lifespan)
app = FastAPI()

static_dir = get_project_root() / "src/visualiser_client/static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/api/")
async def api_root():
    log.info("Hello World")
    return {"message": "Hello World"}

@app.get("/api/circuit/{file:path}", name="path-convertor")
async def get_circuit(file):
    return await project_handler.build_circuit(file)

@app.get("/api/config/{file:path}", name="path-convertor")
async def get_config(file):
    return await project_handler.get_config(file)

# TODO: stream updates
# @app.websocket("/ws/circuit/")
# async def websocket_view(websocket: WebSocket):
#     await websocket.accept()
#     log.info("Websocket accepted")
#     await websocket.send_json(watcher.current_view)
#     async for circuit in watcher.listen_for_circuits():
#         await websocket.send_json(circuit)
