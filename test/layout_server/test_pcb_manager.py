"""Tests for PcbManager."""

import shutil
import tempfile
from pathlib import Path

import pytest

from atopile.layout_server.models import (
    FootprintSummary,
    RenderModel,
)
from atopile.layout_server.pcb_manager import (
    PcbManager,
    _fit_pad_net_text,
    _fit_text_inside_pad,
    _pad_net_text_layer,
    _pad_net_text_rotation,
)

TEST_PCB_V8 = Path("test/common/resources/fileformats/kicad/v8/pcb/test.kicad_pcb")
TEST_PCB_V9 = Path("test/common/resources/fileformats/kicad/v9/pcb/test.kicad_pcb")
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


@pytest.fixture
def manager_v9():
    mgr = PcbManager()
    mgr.load(TEST_PCB_V9)
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
    assert len(model.drawings) > 0
    assert len(model.texts) > 0
    assert len(model.tracks) > 0
    assert len(model.vias) > 0
    assert len(model.board.edges) > 0

    fp = model.footprints[0]
    assert fp.uuid is not None
    assert fp.at is not None
    assert len(fp.pads) >= 0

    assert any(
        f.reference and any(t.text == f.reference for t in f.texts)
        for f in model.footprints
    )
    all_texts = [t for f in model.footprints for t in f.texts]
    assert all(t.text not in ("%R", "%V", "${REFERENCE}") for t in all_texts)
    assert all(t.size is not None for t in all_texts)
    assert any(t.thickness is not None for t in all_texts)
    assert any(t.layer == "F.SilkS" for t in model.texts)
    assert any(d.filled for d in model.drawings)
    assert all(d.width >= 0 for d in model.drawings)
    keepout_zone = next((z for z in model.zones if z.keepout), None)
    assert keepout_zone is not None
    assert keepout_zone.hatch_pitch is not None
    assert keepout_zone.hatch_pitch > 0
    assert len(keepout_zone.outline) >= 3
    silk_text = next((t for t in model.texts if t.text == "ESP32-S3-WROOM"), None)
    assert silk_text is not None
    assert {"left", "bottom"}.issubset(set(silk_text.justify or []))
    pad_net_texts = [
        t
        for footprint in model.footprints
        for t in footprint.texts
        if t.layer is not None and t.layer.endswith(".Nets")
    ]
    assert len(pad_net_texts) > 0
    assert all(
        t.layer != "Annotations.PadNetNames"
        for t in model.texts + [tt for fp in model.footprints for tt in fp.texts]
    )
    assert any(t.text == "GND" for t in pad_net_texts)
    assert all(t.font == "canvas" for t in pad_net_texts)
    assert all(t.size is not None for t in pad_net_texts)
    assert all((t.thickness or 0) > 0 for t in pad_net_texts)
    assert any(t.font == "stroke" for t in all_texts)


def test_get_render_model_v9_zones(manager_v9: PcbManager):
    model = manager_v9.get_render_model()
    assert len(model.zones) > 0
    assert any(len(z.filled_polygons) > 0 for z in model.zones)


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


def test_fit_text_inside_pad_rejects_non_positive_dimensions():
    assert _fit_text_inside_pad("GND", 0.0, 1.0) is None
    assert _fit_text_inside_pad("GND", 1.0, 0.0) is None
    assert _fit_text_inside_pad("GND", -1.0, 1.0) is None


def test_fit_text_inside_pad_stays_bounded_and_orients_with_long_axis():
    # Horizontal pad: bounded fit and thickness range.
    fit_h = _fit_text_inside_pad("GND", 1.2, 0.8)
    assert fit_h is not None
    char_w_h, char_h_h, thickness_h = fit_h
    assert 0 < char_w_h < 1.2
    assert 0 < char_h_h < 0.8
    assert 0.06 <= thickness_h <= 0.20

    # Vertical pad: still bounded.
    fit_v = _fit_text_inside_pad("GND", 0.8, 1.2)
    assert fit_v is not None
    _, char_h_v, thickness_v = fit_v
    assert 0 < char_h_v < 0.8
    assert 0.06 <= thickness_v <= 0.20


def test_pad_net_text_rotation_is_snapped_and_uses_total_rotation():
    # Symmetric pads are always horizontal.
    assert _pad_net_text_rotation(37.0, 1.0, 1.0) == pytest.approx(0.0)

    # Long axis horizontal at 0 deg => horizontal text.
    assert _pad_net_text_rotation(0.0, 1.2, 0.8) == pytest.approx(0.0)

    # Same pad at 90 deg => vertical text.
    assert _pad_net_text_rotation(90.0, 1.2, 0.8) == pytest.approx(90.0)

    # Tall pad with no rotation already has vertical long axis.
    assert _pad_net_text_rotation(0.0, 0.8, 1.2) == pytest.approx(90.0)

    # Tall pad rotated by 90 deg becomes horizontal.
    assert _pad_net_text_rotation(90.0, 0.8, 1.2) == pytest.approx(0.0)

    # Allowed outputs are only 0 and +90.
    for angle in (0, 15, 30, 45, 60, 75, 90, 135, 180, 225, 270, 315):
        snapped = _pad_net_text_rotation(float(angle), 1.2, 0.8)
        assert snapped in {0.0, 90.0}


def test_fit_pad_net_text_uses_shorter_fallbacks_for_small_pads():
    fitted = _fit_pad_net_text("power_in-VCC", 0.79, 0.54)
    assert fitted is not None
    label, metrics = fitted
    assert label == "VCC"
    assert metrics[0] > 0 and metrics[1] > 0


def test_pad_net_text_layer_tracks_pad_copper_layer():
    assert _pad_net_text_layer(["F.Cu", "F.Mask", "F.Paste"]) == "F.Nets"
    assert _pad_net_text_layer(["B.Cu"]) == "B.Nets"
    assert _pad_net_text_layer(["*.Cu", "*.Mask"]) == "*.Nets"
    assert _pad_net_text_layer(["F&B.Cu"]) == "F&B.Nets"
    assert _pad_net_text_layer(["F.Mask", "F.Paste"]) is None
