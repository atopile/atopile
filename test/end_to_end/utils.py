from dataclasses import dataclass
from pathlib import Path

from faebryk.libs.kicad.fileformats import Property, kicad


@dataclass
class PcbSummary:
    num_layers: int
    nets: list[str]
    footprints: list[str]

    @classmethod
    def from_pcb(cls, pcb: kicad.pcb.PcbFile):
        return cls(
            num_layers=len(pcb.kicad_pcb.layers),
            nets=sorted(
                [net.name for net in pcb.kicad_pcb.nets if net.name is not None]
            ),
            footprints=sorted(
                [
                    Property.get_property(footprint.propertys, "Reference")
                    for footprint in pcb.kicad_pcb.footprints
                ],
            ),
        )


def load_pcb_file(pcb_file: Path) -> kicad.pcb.PcbFile:
    return kicad.loads(kicad.pcb.PcbFile, pcb_file.read_text(encoding="utf-8"))


def summarize_pcb_file(pcb_file: Path) -> PcbSummary:
    pcb = load_pcb_file(pcb_file)
    return PcbSummary.from_pcb(pcb)
