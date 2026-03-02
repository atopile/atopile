from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from faebryk.exporters.pcb.deeppcb.transformer import DeepPCB_Transformer
from faebryk.libs.kicad.fileformats import kicad

EXAMPLE_PCBS = sorted(Path("examples").rglob("*.kicad_pcb"))

# Minimal KiCad PCB with diverse pad types for strict round-trip testing.
_DIVERSE_PAD_PCB = """\
(kicad_pcb
\t(version 20241229)
\t(generator "test")
\t(generator_version "0.0.0")
\t(general (thickness 1.6) (legacy_teardrops no))
\t(layers
\t\t(0 "F.Cu" signal)
\t\t(31 "B.Cu" signal)
\t\t(34 "B.Paste" user)
\t\t(35 "F.Paste" user)
\t\t(38 "B.Mask" user)
\t\t(39 "F.Mask" user)
\t\t(44 "Edge.Cuts" user)
\t\t(49 "F.Fab" user)
\t)
\t(setup
\t\t(pad_to_mask_clearance 0)
\t\t(allow_soldermask_bridges_in_footprints no)
\t\t(pcbplotparams
\t\t\t(layerselection 0x00010fc_ffffffff)
\t\t\t(plot_on_all_layers_selection 0x0000000_00000000)
\t\t\t(dashed_line_dash_ratio 12)
\t\t\t(dashed_line_gap_ratio 3)
\t\t\t(svgprecision 4)
\t\t\t(mode 1)
\t\t\t(hpglpennumber 1)
\t\t\t(hpglpenspeed 20)
\t\t\t(hpglpendiameter 15)
\t\t\t(outputformat 1)
\t\t\t(drillshape 1)
\t\t\t(scaleselection 1)
\t\t\t(outputdirectory "")
\t\t)
\t)
\t(net 0 "")
\t(net 1 "VCC")
\t(net 2 "GND")
\t(footprint "TestLib:DiversePads"
\t\t(layer "F.Cu")
\t\t(uuid "aaaaaaaa-1111-2222-3333-444444444444")
\t\t(at 100 100)
\t\t(property "Reference" "U1"
\t\t\t(at 0 -3)
\t\t\t(layer "F.SilkS")
\t\t\t(uuid "bbbbbbbb-1111-2222-3333-444444444444")
\t\t\t(effects (font (size 1 1) (thickness 0.15)))
\t\t)
\t\t(property "Value" "DiversePads"
\t\t\t(at 0 3)
\t\t\t(layer "F.Fab")
\t\t\t(uuid "cccccccc-1111-2222-3333-444444444444")
\t\t\t(effects (font (size 1 1) (thickness 0.15)))
\t\t)
\t\t(pad "1" smd rect
\t\t\t(at -2 0)
\t\t\t(size 1.2 0.6)
\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")
\t\t\t(net 1 "VCC")
\t\t\t(uuid "dddddddd-1111-0001-3333-444444444444")
\t\t)
\t\t(pad "2" smd oval
\t\t\t(at 0 0)
\t\t\t(size 1.8 0.9)
\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")
\t\t\t(net 2 "GND")
\t\t\t(uuid "dddddddd-1111-0002-3333-444444444444")
\t\t)
\t\t(pad "3" thru_hole circle
\t\t\t(at 2 0)
\t\t\t(size 1.6 1.6)
\t\t\t(drill 0.8)
\t\t\t(layers "*.Cu" "F.Mask" "B.Mask")
\t\t\t(net 1 "VCC")
\t\t\t(uuid "dddddddd-1111-0003-3333-444444444444")
\t\t)
\t\t(pad "4" thru_hole oval
\t\t\t(at 4 0)
\t\t\t(size 2.0 1.2)
\t\t\t(drill oval 1.0 0.6)
\t\t\t(layers "*.Cu" "F.Mask" "B.Mask")
\t\t\t(net 2 "GND")
\t\t\t(uuid "dddddddd-1111-0004-3333-444444444444")
\t\t)
\t)
\t(gr_line
\t\t(start 90 90) (end 110 90)
\t\t(stroke (width 0.2) (type default))
\t\t(layer "Edge.Cuts")
\t\t(uuid "eeeeeeee-1111-2222-3333-444444444444")
\t)
\t(gr_line
\t\t(start 110 90) (end 110 110)
\t\t(stroke (width 0.2) (type default))
\t\t(layer "Edge.Cuts")
\t\t(uuid "eeeeeeee-2222-2222-3333-444444444444")
\t)
\t(gr_line
\t\t(start 110 110) (end 90 110)
\t\t(stroke (width 0.2) (type default))
\t\t(layer "Edge.Cuts")
\t\t(uuid "eeeeeeee-3333-2222-3333-444444444444")
\t)
\t(gr_line
\t\t(start 90 110) (end 90 90)
\t\t(stroke (width 0.2) (type default))
\t\t(layer "Edge.Cuts")
\t\t(uuid "eeeeeeee-4444-2222-3333-444444444444")
\t)
)
"""


@pytest.mark.parametrize("pcb_path", EXAMPLE_PCBS, ids=lambda p: str(p))
def test_kicad_to_deeppcb_primitive_counts(pcb_path: Path) -> None:
    pcb_file = kicad.loads(kicad.pcb.PcbFile, pcb_path)
    board = DeepPCB_Transformer.from_kicad_file(pcb_file)

    assert len(board.components) == len(pcb_file.kicad_pcb.footprints)
    assert len(board.wires) == len(pcb_file.kicad_pcb.segments)
    assert len(board.vias) == len(pcb_file.kicad_pcb.vias)
    assert len(board.planes) == len(pcb_file.kicad_pcb.zones)
    assert len(board.nets) == len(pcb_file.kicad_pcb.nets)

    # Native DeepPCB structural sections always exist.
    assert isinstance(board.padstacks, list)
    assert isinstance(board.componentDefinitions, list)
    assert isinstance(board.layers, list)
    assert isinstance(board.netClasses, list)

    edge_has_geometry = any(
        str(getattr(obj, "layer", "")) == "Edge.Cuts"
        for seq in (
            pcb_file.kicad_pcb.gr_lines,
            pcb_file.kicad_pcb.gr_arcs,
            pcb_file.kicad_pcb.gr_polys,
        )
        for obj in seq
    )
    points = (
        board.boundary.get("shape", {}).get("points", [])
        if isinstance(board.boundary, dict)
        else []
    )
    if edge_has_geometry:
        assert len(points) > 0


@pytest.mark.parametrize("pcb_path", EXAMPLE_PCBS, ids=lambda p: str(p))
def test_kicad_deeppcb_roundtrip_native_reconstruction(pcb_path: Path) -> None:
    original = kicad.loads(kicad.pcb.PcbFile, pcb_path).kicad_pcb
    pcb_file = kicad.loads(kicad.pcb.PcbFile, pcb_path)
    board = DeepPCB_Transformer.from_kicad_file(pcb_file)

    roundtrip_file = DeepPCB_Transformer.to_kicad_file(board)
    roundtrip = roundtrip_file.kicad_pcb

    assert len(roundtrip.footprints) == len(original.footprints)
    assert len(roundtrip.segments) == len(original.segments)
    assert len(roundtrip.vias) == len(original.vias)
    assert len(roundtrip.zones) == len(original.zones)
    assert len(roundtrip.nets) == len(original.nets)
    assert len(roundtrip.gr_lines) >= 0


@pytest.mark.parametrize("pcb_path", EXAMPLE_PCBS, ids=lambda p: str(p))
def test_kicad_deeppcb_roundtrip_parity_on_supported_primitives(pcb_path: Path) -> None:
    original = kicad.loads(kicad.pcb.PcbFile, pcb_path).kicad_pcb
    board = DeepPCB_Transformer.from_kicad_file(kicad.loads(kicad.pcb.PcbFile, pcb_path))
    roundtrip = DeepPCB_Transformer.to_kicad_file(board).kicad_pcb

    diff = kicad.compare_without_uuid(original, roundtrip)
    assert isinstance(diff, dict)
    disallowed = [
        path
        for path in diff
        if not path.startswith(
            (
                ".generator",
                ".generator_version",
                ".paper",
                ".setup.",
            )
        )
    ]
    assert disallowed == []


def test_deeppcb_fileformat_load_dump_smoke(tmp_path: Path) -> None:
    pcb_path = EXAMPLE_PCBS[0]
    pcb_file = kicad.loads(kicad.pcb.PcbFile, pcb_path)

    board = DeepPCB_Transformer.from_kicad_file(pcb_file)

    out = tmp_path / "board.deeppcb"
    DeepPCB_Transformer.dumps(board, out)

    loaded = DeepPCB_Transformer.loads(out)

    assert loaded.resolution.get("unit") == "mm"
    assert loaded.resolution.get("value") == 1_000_000
    assert isinstance(loaded.layers, list)
    assert isinstance(loaded.wires, list)


def test_padstack_from_pad_applies_provider_strict_shape_branches() -> None:
    copper_layer_index = {"F.Cu": 0, "B.Cu": 1}

    oval_pad = SimpleNamespace(
        name="1",
        shape="oval",
        type="smd",
        size=SimpleNamespace(w=1.2, h=0.8),
        layers=["F.Cu", "B.Cu"],
        remove_unused_layers=None,
        drill=None,
        options=None,
    )
    oval_id, oval_payload = DeepPCB_Transformer._padstack_from_pad(
        oval_pad,
        copper_layer_index,
        provider_strict=True,
        strict_scope="strict",
    )
    assert oval_payload["shape"]["type"] == "path"
    assert oval_id.startswith("Padstack_Pad_")

    circle_pad = SimpleNamespace(
        name="2",
        shape="circle",
        type="thru_hole",
        size=SimpleNamespace(w=1.0, h=1.0),
        layers=["F.Cu", "B.Cu"],
        remove_unused_layers=None,
        drill=SimpleNamespace(
            shape="circle",
            size_x=0.4,
            size_y=0.4,
            offset=None,
        ),
        options=None,
    )
    circle_id, circle_payload = DeepPCB_Transformer._padstack_from_pad(
        circle_pad,
        copper_layer_index,
        provider_strict=True,
        strict_scope="strict",
    )
    assert "Padstack_Circle_" in circle_id
    assert circle_payload["shape"]["type"] == "circle"


def test_kicad_deeppcb_strict_roundtrip_pad_fidelity(tmp_path: Path) -> None:
    """Full strict pipeline round-trip preserves pad shape, size, type, drill, layers.

    Known acceptable losses:
    - Single-char pad names get "P" prefix (e.g. "1" → "P1")
    - Oval pads may swap w/h since the forward path always encodes travel along Y
    """
    pcb_file = kicad.loads(kicad.pcb.PcbFile, _DIVERSE_PAD_PCB)
    original = pcb_file.kicad_pcb

    # Forward: KiCad → DeepPCB (strict mode strips kicad* hints)
    board = DeepPCB_Transformer.from_kicad_pcb(original, provider_strict=True)

    # Serialize and reload (simulates provider round-trip)
    out = tmp_path / "board.deeppcb"
    DeepPCB_Transformer.dumps(board, out)
    loaded = DeepPCB_Transformer.loads(out)

    # Reverse: DeepPCB → KiCad
    roundtrip = DeepPCB_Transformer.to_internal_pcb(loaded)

    assert len(roundtrip.footprints) == 1
    fp = roundtrip.footprints[0]
    # Strict mode prefixes single-char pad names with "P"
    pads_by_name = {str(p.name): p for p in fp.pads}
    assert len(pads_by_name) == 4, f"Expected 4 pads, got {list(pads_by_name)}"

    # Tolerance for size comparison (mm)
    TOL = 0.02

    # Pad 1: SMD rect, 1.2 x 0.6
    p1 = pads_by_name["P1"]
    assert p1.shape == "rect", f"Pad 1 shape: {p1.shape}"
    assert p1.type == "smd", f"Pad 1 type: {p1.type}"
    assert abs(p1.size.w - 1.2) < TOL, f"Pad 1 width: {p1.size.w}"
    assert abs(p1.size.h - 0.6) < TOL, f"Pad 1 height: {p1.size.h}"
    assert p1.drill is None
    p1_layers = [str(l) for l in p1.layers]
    assert "F.Cu" in p1_layers
    assert "F.Mask" in p1_layers
    assert "F.Paste" in p1_layers

    # Pad 2: SMD oval, 1.8 x 0.9
    # Forward path always encodes oval travel along Y, so w/h may be swapped.
    # We check sorted dimensions instead.
    p2 = pads_by_name["P2"]
    assert p2.shape == "oval", f"Pad 2 shape: {p2.shape}"
    assert p2.type == "smd", f"Pad 2 type: {p2.type}"
    dims2 = sorted([p2.size.w, p2.size.h])
    assert abs(dims2[0] - 0.9) < TOL, f"Pad 2 minor dim: {dims2[0]}"
    assert abs(dims2[1] - 1.8) < TOL, f"Pad 2 major dim: {dims2[1]}"
    assert p2.drill is None
    p2_layers = [str(l) for l in p2.layers]
    assert "F.Cu" in p2_layers
    assert "F.Mask" in p2_layers
    assert "F.Paste" in p2_layers

    # Pad 3: thru_hole circle, 1.6 x 1.6, drill 0.8
    p3 = pads_by_name["P3"]
    assert p3.shape == "circle", f"Pad 3 shape: {p3.shape}"
    assert p3.type == "thru_hole", f"Pad 3 type: {p3.type}"
    assert abs(p3.size.w - 1.6) < TOL, f"Pad 3 width: {p3.size.w}"
    assert abs(p3.size.h - 1.6) < TOL, f"Pad 3 height: {p3.size.h}"
    assert p3.drill is not None, "Pad 3 should have drill"
    assert abs(p3.drill.size_x - 0.8) < TOL, f"Pad 3 drill: {p3.drill.size_x}"
    p3_layers = [str(l) for l in p3.layers]
    assert "*.Cu" in p3_layers or ("F.Cu" in p3_layers and "B.Cu" in p3_layers)
    assert "F.Mask" in p3_layers
    assert "B.Mask" in p3_layers

    # Pad 4: thru_hole oval, 2.0 x 1.2, slot drill 1.0 x 0.6
    p4 = pads_by_name["P4"]
    assert p4.shape == "oval", f"Pad 4 shape: {p4.shape}"
    assert p4.type == "thru_hole", f"Pad 4 type: {p4.type}"
    dims4 = sorted([p4.size.w, p4.size.h])
    assert abs(dims4[0] - 1.2) < TOL, f"Pad 4 minor dim: {dims4[0]}"
    assert abs(dims4[1] - 2.0) < TOL, f"Pad 4 major dim: {dims4[1]}"
    assert p4.drill is not None, "Pad 4 should have drill"
    # Slot drill: check both dimensions are present
    drill_sizes = sorted([p4.drill.size_x, p4.drill.size_y or p4.drill.size_x])
    assert abs(drill_sizes[0] - 0.6) < TOL, f"Pad 4 drill minor: {drill_sizes[0]}"
    assert abs(drill_sizes[1] - 1.0) < TOL, f"Pad 4 drill major: {drill_sizes[1]}"
    p4_layers = [str(l) for l in p4.layers]
    assert "*.Cu" in p4_layers or ("F.Cu" in p4_layers and "B.Cu" in p4_layers)
    assert "F.Mask" in p4_layers
    assert "B.Mask" in p4_layers


@pytest.mark.parametrize("pcb_path", EXAMPLE_PCBS, ids=lambda p: str(p))
def test_kicad_deeppcb_strict_roundtrip_counts(pcb_path: Path, tmp_path: Path) -> None:
    """Strict round-trip preserves footprint count and pad count per footprint."""
    pcb_file = kicad.loads(kicad.pcb.PcbFile, pcb_path)
    original = pcb_file.kicad_pcb

    board = DeepPCB_Transformer.from_kicad_pcb(original, provider_strict=True)

    out = tmp_path / "board.deeppcb"
    DeepPCB_Transformer.dumps(board, out)
    loaded = DeepPCB_Transformer.loads(out)

    roundtrip = DeepPCB_Transformer.to_internal_pcb(loaded)

    assert len(roundtrip.footprints) == len(original.footprints), (
        f"Footprint count mismatch: {len(roundtrip.footprints)} vs {len(original.footprints)}"
    )

    for orig_fp, rt_fp in zip(original.footprints, roundtrip.footprints):
        assert len(rt_fp.pads) == len(orig_fp.pads), (
            f"Pad count mismatch in {getattr(orig_fp, 'name', '?')}: "
            f"{len(rt_fp.pads)} vs {len(orig_fp.pads)}"
        )


_REUSE_BLOCK_PCBS = [
    p
    for p in EXAMPLE_PCBS
    if "esp32_minimal" in str(p) and p.name == "esp32_minimal.kicad_pcb"
]


@pytest.mark.parametrize("pcb_path", _REUSE_BLOCK_PCBS, ids=lambda p: str(p))
def test_reuse_block_preserves_all_padstacks(pcb_path: Path, tmp_path: Path) -> None:
    """Reuse block collapsing must preserve all padstacks from collapsed footprints.

    The DeepPCB API requires through-hole padstacks (e.g. circular drill pads)
    to be present even when the component that uses them is collapsed into a
    reuse block. Without them, the board silently fails during API ingestion.
    """
    project_root = pcb_path.parent.parent.parent  # layouts/build_target/file -> project
    pcb_file = kicad.loads(kicad.pcb.PcbFile, pcb_path)

    # Generate without reuse blocks (all padstacks preserved)
    board_no_reuse = DeepPCB_Transformer.from_kicad_file(
        pcb_file, provider_strict=True
    )
    all_padstack_ids = {ps["id"] for ps in board_no_reuse.padstacks}

    # Generate with reuse blocks
    metadata: dict = {}
    board_reuse = DeepPCB_Transformer.from_kicad_file(
        pcb_file,
        project_root=project_root,
        provider_strict=True,
        reuse_block_metadata_out=metadata,
    )

    if not metadata:
        pytest.skip("No reuse blocks found")

    reuse_padstack_ids = {ps["id"] for ps in board_reuse.padstacks}

    # All padstacks from the non-reuse version must be present in the reuse version
    missing = all_padstack_ids - reuse_padstack_ids
    assert not missing, (
        f"Reuse block collapsing dropped {len(missing)} padstack(s): {missing}"
    )

    # Through-hole padstacks specifically must be preserved
    th_no_reuse = {
        ps["id"]
        for ps in board_no_reuse.padstacks
        if ps.get("layers") == [0, 1]
    }
    th_reuse = {
        ps["id"]
        for ps in board_reuse.padstacks
        if ps.get("layers") == [0, 1]
    }
    missing_th = th_no_reuse - th_reuse
    assert not missing_th, (
        f"Through-hole padstacks dropped by reuse blocks: {missing_th}"
    )
