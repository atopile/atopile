from pathlib import Path

from test.end_to_end.conftest import dump_and_run
from test.end_to_end.utils import get_footprint_value, summarize_pcb_file


def test_resistor_voltage_divider_builds(tmp_path: Path):
    pcb_file = tmp_path / Path("layout/app/app.kicad_pcb")
    assert not pcb_file.exists()

    _, stderr, p = dump_and_run(
        """
        import ResistorVoltageDivider

        module App:
            vdiv = new ResistorVoltageDivider

            vdiv.v_in = 10V +/- 1%
            assert vdiv.v_out within 3V to 3.2V
            assert vdiv.current within 1mA to 3mA
        """,
        [],
        working_dir=tmp_path,
    )

    assert p.returncode == 0, stderr
    assert pcb_file.exists()
    assert "Creating new layout" in stderr

    summary = summarize_pcb_file(pcb_file)
    assert summary.footprints == ["R1", "R2"]
    assert len(summary.nets) == 3

    r_top = get_footprint_value(pcb_file, "R1")
    r_bottom = get_footprint_value(pcb_file, "R2")
    expected_r_top_ohms = 4700
    expected_r_bottom_ohms = 2000
    assert (r_top, r_bottom) == (
        f"{expected_r_top_ohms}Ω",
        f"{expected_r_bottom_ohms}Ω",
    )

    ratio = expected_r_bottom_ohms / (expected_r_top_ohms + expected_r_bottom_ohms)
    assert 3 / 10.1 <= ratio <= 3.2 / 9.9
