from __future__ import annotations

from pathlib import Path

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
def test_kicad_deeppcb_roundtrip_matches_kicad_canonical(pcb_path: Path) -> None:
    # Compare canonicalized KiCad text because source files may not already be in
    # canonical dump format.
    canonical_original = kicad.dumps(kicad.loads(kicad.pcb.PcbFile, pcb_path))

    pcb_file = kicad.loads(kicad.pcb.PcbFile, pcb_path)
    board = DeepPCB_Transformer.from_kicad_file(
        pcb_file,
        include_lossless_source=True,
    )

    roundtrip_file = DeepPCB_Transformer.to_kicad_file(board)
    canonical_roundtrip = kicad.dumps(roundtrip_file)

    assert canonical_roundtrip == canonical_original


def test_deeppcb_fileformat_load_dump_smoke(tmp_path: Path) -> None:
    pcb_path = EXAMPLE_PCBS[0]
    pcb_file = kicad.loads(kicad.pcb.PcbFile, pcb_path)

    board = DeepPCB_Transformer.from_kicad_file(
        pcb_file,
        include_lossless_source=True,
    )

    out = tmp_path / "board.deeppcb"
    DeepPCB_Transformer.dumps(board, out)

    loaded = DeepPCB_Transformer.loads(out)

    assert loaded.resolution.get("unit") == "mm"
    assert loaded.resolution.get("value") == 1000
    assert isinstance(loaded.layers, list)
    assert isinstance(loaded.wires, list)
