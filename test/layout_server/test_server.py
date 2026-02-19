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
    assert "drawings" in model
    assert "texts" in model
    assert "tracks" in model
    assert "board" in model
    assert isinstance(model["drawings"], list)
    assert isinstance(model["texts"], list)
    assert all("filled" in d for d in model["drawings"])
    assert isinstance(model["footprints"], list)
    assert len(model["footprints"]) > 0
    fp = model["footprints"][0]
    assert "x" in fp["at"]
    assert "y" in fp["at"]
    assert "texts" in fp
    assert isinstance(fp["texts"], list)

    texts = [t for footprint in model["footprints"] for t in footprint.get("texts", [])]
    assert all("text" in t for t in texts)
    assert all("at" in t for t in texts)
    assert all("layer" in t for t in texts)
    assert all("size" in t for t in texts)
    assert all("thickness" in t for t in texts)
    assert all("justify" in t for t in texts)
    assert all(t.get("text") not in ("%R", "%V", "${REFERENCE}") for t in texts)
    if model.get("zones"):
        zone = model["zones"][0]
        assert "keepout" in zone
        assert "hatch_mode" in zone
        assert "hatch_pitch" in zone
        assert "fill_enabled" in zone


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
    assert data["code"] == "ok"


@pytest.mark.anyio
async def test_undo_empty(client: AsyncClient):
    resp = await client.post("/api/undo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert data["code"] == "nothing_to_undo"


@pytest.mark.anyio
async def test_redo_empty(client: AsyncClient):
    resp = await client.post("/api/redo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert data["code"] == "nothing_to_redo"


@pytest.mark.anyio
async def test_execute_action_rotate(client: AsyncClient):
    fps_resp = await client.get("/api/footprints")
    fps = fps_resp.json()
    uuid = fps[0]["uuid"]

    resp = await client.post(
        "/api/execute-action",
        json={"command": "rotate_footprint", "uuid": uuid, "delta_degrees": 90},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["code"] == "ok"


@pytest.mark.anyio
async def test_execute_action_move(client: AsyncClient):
    fps_resp = await client.get("/api/footprints")
    fps = fps_resp.json()
    uuid = fps[0]["uuid"]

    resp = await client.post(
        "/api/execute-action",
        json={"command": "move_footprint", "uuid": uuid, "x": 10.0, "y": 20.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["code"] == "ok"


@pytest.mark.anyio
async def test_execute_action_flip(client: AsyncClient):
    fps_resp = await client.get("/api/footprints")
    fps = fps_resp.json()
    uuid = fps[0]["uuid"]
    orig_layer = fps[0]["layer"]

    resp = await client.post(
        "/api/execute-action",
        json={"command": "flip_footprint", "uuid": uuid},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["code"] == "ok"

    # Verify layer flipped
    fps_after = await client.get("/api/footprints")
    flipped = next(f for f in fps_after.json() if f["uuid"] == uuid)
    expected = "B.Cu" if orig_layer == "F.Cu" else "F.Cu"
    assert flipped["layer"] == expected


@pytest.mark.anyio
async def test_execute_action_unknown(client: AsyncClient):
    resp = await client.post(
        "/api/execute-action",
        json={"command": "nonexistent"},
    )
    assert resp.status_code == 422
