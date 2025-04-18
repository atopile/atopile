# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import tempfile
from pathlib import Path

from kicadcliwrapper.generated.kicad_cli import kicad_cli as k

from faebryk.libs.kicad.fileformats_latest import C_kicad_drc_report_file


def run_drc(pcb: Path):
    drc_report = None
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        out = tmpdir / "drc.json"
        k(
            k.pcb(
                k.pcb.drc(
                    INPUT_FILE=str(pcb),
                    format="json",
                    output=str(out),
                    severity_all=True,
                    schematic_parity=False,
                )
            )
        ).exec(check=True)

        drc_report = C_kicad_drc_report_file.loads(out)

    return drc_report
