import json as json
import logging
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from atopile.visualiser.render import render

# FIXME: https://github.com/tiangolo/fastapi/issues/1508
log = logging.Logger(__name__, level=logging.DEBUG)
log.warning("Test!")  # FIXME: this should be debug, but can't be because the logs don't output otherwise

app = FastAPI()

app.mount("/static", StaticFiles(directory="src/visualiser_client/static"), name="static")

@app.get("/api/")
async def api_root():
    return {"message": "Hello World"}

@app.post("/api/graph")
async def post_graph(data: Dict[Any, Any]):
    # this is where the `data` comes back to!
    log.warning(str(data))  # FIXME:
    return {"message": "OK"}
# @app.get("/api/graph")
# async def get_graph():
#     # call render.py to get a dict of the current circuit
#     with open("output.json", "r") as f:
#     # Load the contents of the file into a Python object
#         data = json.load(f)
#     return data
    # return {
    #     "cells": [
    # {
    #   "type": "standard.Rectangle",
    #   "position": {
    #     "x": 100,
    #     "y": 30
    #   },
    #   "size": {
    #     "width": 100,
    #     "height": 40
    #   },
    #   "angle": 0,
    #   "id": "1f9f2843-2015-4784-a1d5-c3745423b5e1",
    #   "z": 1,
    #   "attrs": {
    #     "body": {
    #       "fill": "blue"
    #     },
    #     "label": {
    #       "fill": "white",
    #       "text": "Hello"
    #     }}},
    #     {
    #         "id": 1,
    #         "type": 'standard.Rectangle',
    #         "position": {
    #             "x": 200,
    #             "y": 100
    #         },
    #         "size": {
    #             "width": 100,
    #             "height": 100
    #         }
    #     }]
    # }
