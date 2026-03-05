import re
from dataclasses import dataclass
from pathlib import Path

from faebryk.library._F import Units
from faebryk.libs.kicad.fileformats import Property, kicad

_VALUE_PREFIX_RE = re.compile(
    r"^\s*"
    r"(?P<value>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
    r"\s*"
    r"(?P<prefix>[A-Za-zµμ]{0,2})"
    r"(?P<unit>[A-Za-zΩ]+)?"
)


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


def parse_numeric_display_value(value: str) -> float:
    match = _VALUE_PREFIX_RE.match(value)
    if match is None:
        raise ValueError(f"Could not parse numeric value from {value!r}")

    prefix = match.group("prefix")
    prefix_scale = {"": 1.0, **Units.is_si_prefixed_unit.SI_PREFIXES, "μ": 1e-6}.get(
        prefix
    )
    if prefix_scale is None:
        raise ValueError(f"Unknown SI prefix {prefix!r} in {value!r}")

    return float(match.group("value")) * prefix_scale


def get_footprint_value(pcb_file: Path, reference: str) -> str:
    pcb = load_pcb_file(pcb_file)

    for footprint in pcb.kicad_pcb.footprints:
        if Property.get_property(footprint.propertys, "Reference") == reference:
            return Property.get_property(footprint.propertys, "Value")

    raise ValueError(f"Footprint {reference!r} not found in {pcb_file}")


def summarize_pcb_file(pcb_file: Path) -> PcbSummary:
    pcb = load_pcb_file(pcb_file)
    return PcbSummary.from_pcb(pcb)
