from dataclasses import dataclass
from pathlib import Path

from faebryk.libs.kicad.fileformats_latest import C_kicad_pcb_file
from test.end_to_end.conftest import dump_and_run


@dataclass
class PcbSummary:
    num_layers: int
    nets: list[str]
    footprints: list[str]

    @classmethod
    def from_pcb(cls, pcb: C_kicad_pcb_file):
        return cls(
            num_layers=len(pcb.kicad_pcb.layers),
            nets=sorted([net.name for net in pcb.kicad_pcb.nets]),
            footprints=sorted(
                [
                    footprint.propertys.get("Reference").value
                    for footprint in pcb.kicad_pcb.footprints
                ],
            ),
        )

    def add_net(self, net: str) -> "PcbSummary":
        return PcbSummary(
            num_layers=self.num_layers,
            nets=sorted(self.nets + [net]),
            footprints=self.footprints,
        )

    def add_footprint(self, footprint: str) -> "PcbSummary":
        return PcbSummary(
            num_layers=self.num_layers,
            nets=self.nets,
            footprints=sorted(self.footprints + [footprint]),
        )


def summarize_pcb_file(pcb_file: Path) -> PcbSummary:
    pcb = C_kicad_pcb_file.loads(pcb_file.read_text(encoding="utf-8"))
    return PcbSummary.from_pcb(pcb)


SIMPLE_APP = """
import Resistor
module App:
    a = new Resistor
"""

SIMPLE_APP_PCB_SUMMARY = PcbSummary(
    num_layers=29,
    nets=["", "a-net-0", "a-net-1"],
    footprints=["R1"],
)


def test_empty_design(tmpdir: Path):
    pcb_file = tmpdir / Path("layout/app/app.kicad_pcb")
    assert not pcb_file.exists()

    app = """
    module App:
        signal a
    """

    _, stderr, p = dump_and_run(app, [], working_dir=tmpdir)

    assert p.returncode == 0
    assert pcb_file.exists()
    assert "Creating new layout" in stderr

    assert summarize_pcb_file(pcb_file) == PcbSummary(
        num_layers=29, nets=[""], footprints=[]
    )


def test_pcb_file_created(tmpdir: Path):
    pcb_file = tmpdir / Path("layout/app/app.kicad_pcb")
    assert not pcb_file.exists()

    _, stderr, p = dump_and_run(SIMPLE_APP, [], working_dir=tmpdir)

    assert p.returncode == 0
    assert pcb_file.exists()
    assert "Creating new layout" in stderr

    assert SIMPLE_APP_PCB_SUMMARY == summarize_pcb_file(pcb_file)


def test_pcb_file_addition(tmpdir: Path):
    pcb_file = tmpdir / Path("layout/app/app.kicad_pcb")
    assert not pcb_file.exists()

    _, stderr, p = dump_and_run(SIMPLE_APP, [], working_dir=tmpdir)
    assert p.returncode == 0
    assert pcb_file.exists()
    assert "Creating new layout" in stderr
    assert SIMPLE_APP_PCB_SUMMARY == summarize_pcb_file(pcb_file)

    _, stderr, p = dump_and_run(
        f"{SIMPLE_APP}\n    b = new Resistor",
        [],
        working_dir=tmpdir,
    )
    assert p.returncode == 0
    assert "Creating new layout" not in stderr
    assert (
        SIMPLE_APP_PCB_SUMMARY.add_net("b-net-0").add_net("b-net-1").add_footprint("R2")
    ) == summarize_pcb_file(pcb_file)


def test_pcb_file_removal(tmpdir: Path):
    pcb_file = tmpdir / Path("layout/app/app.kicad_pcb")
    assert not pcb_file.exists()

    _, stderr, p = dump_and_run(
        f"{SIMPLE_APP}\n    b = new Resistor",
        [],
        working_dir=tmpdir,
    )
    assert p.returncode == 0
    assert "Creating new layout" in stderr
    assert (
        SIMPLE_APP_PCB_SUMMARY.add_net("b-net-0").add_net("b-net-1").add_footprint("R2")
    ) == summarize_pcb_file(pcb_file)

    _, stderr, p = dump_and_run(SIMPLE_APP, [], working_dir=tmpdir)
    assert p.returncode == 0
    assert "Creating new layout" not in stderr
    assert SIMPLE_APP_PCB_SUMMARY == summarize_pcb_file(pcb_file)
