"""Tests for PcbManager."""

import shutil
import tempfile
from pathlib import Path

import pytest

from atopile.layout_server.pcb_manager import PcbManager

TEST_PCB_V8 = Path("test/common/resources/fileformats/kicad/v8/pcb/test.kicad_pcb")
ESP32_PCB = Path("examples/esp32_minimal/layouts/esp32_minimal/esp32_minimal.kicad_pcb")


@pytest.fixture
def manager_v8():
    mgr = PcbManager()
    mgr.load(TEST_PCB_V8)
    return mgr


@pytest.fixture
def manager_esp32():
    mgr = PcbManager()
    mgr.load(ESP32_PCB)
    return mgr


def test_load_v8(manager_v8: PcbManager):
    fps = manager_v8.get_footprints()
    assert len(fps) > 0
    for fp in fps:
        assert "uuid" in fp
        assert "x" in fp
        assert "y" in fp


def test_load_esp32(manager_esp32: PcbManager):
    fps = manager_esp32.get_footprints()
    assert len(fps) >= 10
    refs = [fp["reference"] for fp in fps if fp["reference"]]
    assert any(r.startswith("C") for r in refs)


def test_get_render_model_v8(manager_v8: PcbManager):
    model = manager_v8.get_render_model()
    assert "footprints" in model
    assert "tracks" in model
    assert "vias" in model
    assert "board" in model
    assert "nets" in model
    assert isinstance(model["footprints"], list)


def test_get_render_model_esp32(manager_esp32: PcbManager):
    model = manager_esp32.get_render_model()
    assert len(model["footprints"]) >= 10
    assert len(model["tracks"]) > 0
    assert len(model["vias"]) > 0
    assert len(model["board"]["edges"]) > 0

    # Check footprint structure
    fp = model["footprints"][0]
    assert "uuid" in fp
    assert "at" in fp
    assert "pads" in fp
    assert len(fp["at"]) == 3


def test_move_footprint(manager_v8: PcbManager):
    fps = manager_v8.get_footprints()
    uuid = fps[0]["uuid"]

    manager_v8.move_footprint(uuid, 99.0, 88.0)

    fps_after = manager_v8.get_footprints()
    moved = next(f for f in fps_after if f["uuid"] == uuid)
    assert moved["x"] == pytest.approx(99.0)
    assert moved["y"] == pytest.approx(88.0)


def test_move_footprint_not_found(manager_v8: PcbManager):
    with pytest.raises(ValueError, match="not found"):
        manager_v8.move_footprint("nonexistent-uuid", 0, 0)


def test_save_roundtrip():
    with tempfile.NamedTemporaryFile(suffix=".kicad_pcb", delete=False) as tmp:
        shutil.copy2(TEST_PCB_V8, tmp.name)
        tmp_path = Path(tmp.name)

    try:
        mgr = PcbManager()
        mgr.load(tmp_path)
        fps = mgr.get_footprints()
        uuid = fps[0]["uuid"]

        mgr.move_footprint(uuid, 123.45, 67.89)
        mgr.save()

        # Reload and verify
        mgr2 = PcbManager()
        mgr2.load(tmp_path)
        fps2 = mgr2.get_footprints()
        moved = next(f for f in fps2 if f["uuid"] == uuid)
        assert moved["x"] == pytest.approx(123.45, abs=0.01)
        assert moved["y"] == pytest.approx(67.89, abs=0.01)
    finally:
        tmp_path.unlink()
