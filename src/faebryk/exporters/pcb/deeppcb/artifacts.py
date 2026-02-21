from __future__ import annotations

from pathlib import Path
from typing import Any

from faebryk.exporters.pcb.deeppcb.transformer import DeepPCB_Transformer
from faebryk.libs.kicad.fileformats import kicad


def export_deeppcb(
    pcb_file: Path,
    deeppcb_file: Path,
    *,
    include_lossless_source: bool = False,
) -> None:
    """Export a KiCad PCB file to native DeepPCB JSON artifact."""
    parsed = kicad.loads(kicad.pcb.PcbFile, pcb_file)
    board = DeepPCB_Transformer.from_kicad_file(
        parsed,
        include_lossless_source=include_lossless_source,
    )
    DeepPCB_Transformer.dumps(board, deeppcb_file)


def export_deeppcb_from_kicad_pcb(
    pcb: Any,
    deeppcb_file: Path,
    *,
    include_lossless_source: bool = False,
) -> None:
    """Export from an already-parsed KiCad PCB object."""
    board = DeepPCB_Transformer.from_kicad_pcb(
        pcb,
        include_lossless_source=include_lossless_source,
    )
    DeepPCB_Transformer.dumps(board, deeppcb_file)
