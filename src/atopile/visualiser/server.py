from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="src/visualiser_client/static"), name="static")

@app.get("/api/")
async def api_root():
    return {"message": "Hello World"}

@app.get("/api/graph")
async def get_graph():
    return {
        "cells": [{
            "id": 1,
            "type": 'standard.Rectangle',
            "position": {
                "x": 100,
                "y": 100
            },
            "size": {
                "width": 100,
                "height": 100
            }
        }]
    }
