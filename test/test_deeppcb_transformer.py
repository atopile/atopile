from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from faebryk.exporters.pcb.deeppcb.transformer import DeepPCB_Transformer
from faebryk.libs.kicad.fileformats import kicad

EXAMPLE_PCBS = sorted(Path("examples").rglob("*.kicad_pcb"))


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
