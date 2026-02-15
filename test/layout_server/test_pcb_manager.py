"""Tests for PcbManager."""

import shutil
import tempfile
from pathlib import Path

import pytest

from atopile.layout_server.models import (
    FootprintSummary,
    RenderModel,
)
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
        assert isinstance(fp, FootprintSummary)
        assert fp.uuid is not None


def test_load_esp32(manager_esp32: PcbManager):
    fps = manager_esp32.get_footprints()
    assert len(fps) >= 10
    refs = [fp.reference for fp in fps if fp.reference]
    assert any(r.startswith("C") for r in refs)


def test_get_render_model_v8(manager_v8: PcbManager):
    model = manager_v8.get_render_model()
    assert isinstance(model, RenderModel)
    assert isinstance(model.footprints, list)


def test_get_render_model_esp32(manager_esp32: PcbManager):
    model = manager_esp32.get_render_model()
    assert len(model.footprints) >= 10
    assert len(model.tracks) > 0
    assert len(model.vias) > 0
    assert len(model.board.edges) > 0

    fp = model.footprints[0]
    assert fp.uuid is not None
    assert fp.at is not None
    assert len(fp.pads) >= 0


def test_move_footprint(manager_v8: PcbManager):
    fps = manager_v8.get_footprints()
    uuid = fps[0].uuid

    manager_v8.move_footprint(uuid, 99.0, 88.0)

    fps_after = manager_v8.get_footprints()
    moved = next(f for f in fps_after if f.uuid == uuid)
    assert moved.x == pytest.approx(99.0)
    assert moved.y == pytest.approx(88.0)


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
        uuid = fps[0].uuid

        mgr.move_footprint(uuid, 123.45, 67.89)
        mgr.save()

        mgr2 = PcbManager()
        mgr2.load(tmp_path)
        fps2 = mgr2.get_footprints()
        moved = next(f for f in fps2 if f.uuid == uuid)
        assert moved.x == pytest.approx(123.45, abs=0.01)
        assert moved.y == pytest.approx(67.89, abs=0.01)
    finally:
        tmp_path.unlink()


# --- Undo / Redo tests ---


def test_undo_move(manager_v8: PcbManager):
    fps = manager_v8.get_footprints()
    uuid = fps[0].uuid
    orig_x, orig_y = fps[0].x, fps[0].y

    manager_v8.move_footprint(uuid, 50.0, 60.0)
    after_move = next(f for f in manager_v8.get_footprints() if f.uuid == uuid)
    assert after_move.x == pytest.approx(50.0)

    assert manager_v8.undo()
    after_undo = next(f for f in manager_v8.get_footprints() if f.uuid == uuid)
    assert after_undo.x == pytest.approx(orig_x)
    assert after_undo.y == pytest.approx(orig_y)


def test_redo_move(manager_v8: PcbManager):
    fps = manager_v8.get_footprints()
    uuid = fps[0].uuid

    manager_v8.move_footprint(uuid, 50.0, 60.0)
    manager_v8.undo()

    assert manager_v8.redo()
    after_redo = next(f for f in manager_v8.get_footprints() if f.uuid == uuid)
    assert after_redo.x == pytest.approx(50.0)
    assert after_redo.y == pytest.approx(60.0)


def test_undo_empty(manager_v8: PcbManager):
    assert not manager_v8.undo()


def test_redo_empty(manager_v8: PcbManager):
    assert not manager_v8.redo()


def test_redo_cleared_after_new_action(manager_v8: PcbManager):
    fps = manager_v8.get_footprints()
    uuid = fps[0].uuid

    manager_v8.move_footprint(uuid, 10.0, 20.0)
    manager_v8.undo()
    assert manager_v8.can_redo

    manager_v8.move_footprint(uuid, 30.0, 40.0)
    assert not manager_v8.can_redo


# --- Rotate tests ---


def test_rotate_footprint(manager_v8: PcbManager):
    fps = manager_v8.get_footprints()
    uuid = fps[0].uuid
    orig_r = fps[0].r

    manager_v8.rotate_footprint(uuid, 90.0)
    after = next(f for f in manager_v8.get_footprints() if f.uuid == uuid)
    assert after.r == pytest.approx((orig_r + 90.0) % 360)


def test_undo_rotate(manager_v8: PcbManager):
    fps = manager_v8.get_footprints()
    uuid = fps[0].uuid
    orig_r = fps[0].r

    manager_v8.rotate_footprint(uuid, 90.0)
    manager_v8.undo()

    after = next(f for f in manager_v8.get_footprints() if f.uuid == uuid)
    assert after.r == pytest.approx(orig_r)


# --- Flip tests ---


def test_flip_footprint(manager_v8: PcbManager):
    fps = manager_v8.get_footprints()
    uuid = fps[0].uuid
    orig_layer = fps[0].layer

    manager_v8.flip_footprint(uuid)

    after = next(f for f in manager_v8.get_footprints() if f.uuid == uuid)
    expected = "B.Cu" if orig_layer == "F.Cu" else "F.Cu"
    assert after.layer == expected


def test_undo_flip(manager_v8: PcbManager):
    fps = manager_v8.get_footprints()
    uuid = fps[0].uuid
    orig_layer = fps[0].layer

    manager_v8.flip_footprint(uuid)
    manager_v8.undo()

    after = next(f for f in manager_v8.get_footprints() if f.uuid == uuid)
    assert after.layer == orig_layer


def test_flip_roundtrip(manager_v8: PcbManager):
    fps = manager_v8.get_footprints()
    uuid = fps[0].uuid
    orig_layer = fps[0].layer

    manager_v8.flip_footprint(uuid)
    manager_v8.flip_footprint(uuid)

    after = next(f for f in manager_v8.get_footprints() if f.uuid == uuid)
    assert after.layer == orig_layer
