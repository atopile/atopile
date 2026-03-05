from pathlib import Path

from test.end_to_end.conftest import dump_and_run
from test.end_to_end.utils import PcbSummary, summarize_pcb_file

SIMPLE_APP = """
import Resistor
module App:
    a = new Resistor
"""

SIMPLE_APP_PCB_SUMMARY = PcbSummary(
    num_layers=29,
    nets=["unnamed[0]", "unnamed[1]"],
    footprints=["R1"],
)


def test_empty_design(tmp_path: Path):
    pcb_file = tmp_path / Path("layout/app/app.kicad_pcb")
    assert not pcb_file.exists()

    app = """
    module App:
        signal a
    """

    stdout, stderr, p = dump_and_run(app, [], working_dir=tmp_path)

    assert p.returncode == 0
    assert pcb_file.exists()
    assert "Creating new layout" in stderr

    assert summarize_pcb_file(pcb_file) == PcbSummary(
        num_layers=29, nets=[], footprints=[]
    )


def test_pcb_file_created(tmp_path: Path):
    pcb_file = tmp_path / Path("layout/app/app.kicad_pcb")
    assert not pcb_file.exists()

    stdout, stderr, p = dump_and_run(SIMPLE_APP, [], working_dir=tmp_path)

    assert p.returncode == 0
    assert pcb_file.exists()
    assert "Creating new layout" in stderr

    assert SIMPLE_APP_PCB_SUMMARY == summarize_pcb_file(pcb_file)


def test_pcb_file_addition(tmp_path: Path):
    pcb_file = tmp_path / Path("layout/app/app.kicad_pcb")
    assert not pcb_file.exists()

    stdout, stderr, p = dump_and_run(SIMPLE_APP, [], working_dir=tmp_path)
    assert p.returncode == 0
    assert pcb_file.exists()
    assert "Creating new layout" in stderr
    assert SIMPLE_APP_PCB_SUMMARY == summarize_pcb_file(pcb_file)

    stdout, stderr, p = dump_and_run(
        f"{SIMPLE_APP}\n    b = new Resistor",
        [],
        working_dir=tmp_path,
    )
    assert p.returncode == 0
    assert "Creating new layout" not in stderr
    # When two resistors exist, net names get prefixed to disambiguate conflicts
    # Format: <owner>.-<base_name>
    expected = PcbSummary(
        num_layers=SIMPLE_APP_PCB_SUMMARY.num_layers,
        nets=sorted(
            [
                "unnamed[0]",
                "unnamed[1]",
                "b-unnamed[0]",
                "b-unnamed[1]",
            ]
        ),
        footprints=["R1", "R2"],
    )
    assert expected == summarize_pcb_file(pcb_file)


def test_pcb_file_removal(tmp_path: Path):
    pcb_file = tmp_path / Path("layout/app/app.kicad_pcb")
    assert not pcb_file.exists()

    stdout, stderr, p = dump_and_run(
        f"{SIMPLE_APP}\n    b = new Resistor",
        [],
        working_dir=tmp_path,
    )
    assert p.returncode == 0
    assert "Creating new layout" in stderr
    # When two resistors exist, net names get prefixed to disambiguate conflicts
    expected_with_two = PcbSummary(
        num_layers=SIMPLE_APP_PCB_SUMMARY.num_layers,
        nets=sorted(
            [
                "unnamed[0]",
                "unnamed[1]",
                "b-unnamed[0]",
                "b-unnamed[1]",
            ]
        ),
        footprints=["R1", "R2"],
    )
    assert expected_with_two == summarize_pcb_file(pcb_file)

    stdout, stderr, p = dump_and_run(SIMPLE_APP, [], working_dir=tmp_path)
    assert p.returncode == 0
    assert "Creating new layout" not in stderr
    assert SIMPLE_APP_PCB_SUMMARY == summarize_pcb_file(pcb_file)
