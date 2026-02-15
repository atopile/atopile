"""Tests for the layout server FastAPI app."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from atopile.layout_server.server import create_app

TEST_PCB = Path("test/common/resources/fileformats/kicad/v8/pcb/test.kicad_pcb")


@pytest.fixture
def app():
    return create_app(TEST_PCB)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_index(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "PCB Layout Editor" in resp.text


@pytest.mark.anyio
async def test_render_model(client: AsyncClient):
    resp = await client.get("/api/render-model")
    assert resp.status_code == 200
    model = resp.json()
    assert "footprints" in model
    assert "tracks" in model
    assert "board" in model
    assert isinstance(model["footprints"], list)
    assert len(model["footprints"]) > 0
    # Verify pydantic structure: footprint at is an object
    fp = model["footprints"][0]
    assert "x" in fp["at"]
    assert "y" in fp["at"]


@pytest.mark.anyio
async def test_footprints(client: AsyncClient):
    resp = await client.get("/api/footprints")
    assert resp.status_code == 200
    fps = resp.json()
    assert isinstance(fps, list)
    assert len(fps) > 0
    assert "uuid" in fps[0]
    assert "reference" in fps[0]


@pytest.mark.anyio
async def test_reload(client: AsyncClient):
    resp = await client.post("/api/reload")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.anyio
async def test_undo_empty(client: AsyncClient):
    resp = await client.post("/api/undo")
    assert resp.status_code == 200
    assert resp.json()["status"] == "nothing_to_undo"


@pytest.mark.anyio
async def test_redo_empty(client: AsyncClient):
    resp = await client.post("/api/redo")
    assert resp.status_code == 200
    assert resp.json()["status"] == "nothing_to_redo"


@pytest.mark.anyio
async def test_rotate_footprint(client: AsyncClient):
    fps_resp = await client.get("/api/footprints")
    fps = fps_resp.json()
    uuid = fps[0]["uuid"]

    resp = await client.post(
        "/api/rotate-footprint",
        json={"uuid": uuid, "angle": 90},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
