from fastapi import FastAPI, Body
from pydantic import BaseModel

from fastapi import HTTPException

from atopile.components import Resistor, Inductor, Capacitor
from atopile.database.fake_db import fetch_from_db

app = FastAPI()


# This will store the messages received
data_storage = []

@app.get("/")
async def root():
    return {"messages": data_storage}


@app.post("/resistor")
async def get_resistor(resistor_data: Resistor):
    try:
        data = fetch_from_db(resistor_data)
        return data
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
