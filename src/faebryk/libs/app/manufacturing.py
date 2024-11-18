# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from faebryk.core.module import Module
from faebryk.exporters.bom.jlcpcb import write_bom_jlcpcb
from faebryk.exporters.pcb.kicad.artifacts import (
    export_dxf,
    export_gerber,
    export_glb,
    export_pick_and_place,
    export_step,
)
from faebryk.exporters.pcb.pick_and_place.jlcpcb import (
    convert_kicad_pick_and_place_to_jlcpcb,
)

logger = logging.getLogger(__name__)


def export_pcba_artifacts(out: Path, pcb_path: Path, app: Module):
    cad_path = out.joinpath("cad")
    cad_path.mkdir(parents=True, exist_ok=True)

    logger.info("Exporting PCBA artifacts")

    write_bom_jlcpcb(
        app.get_children_modules(types=Module), out.joinpath("jlcpcb_bom.csv")
    )
    export_step(pcb_path, step_file=cad_path.joinpath("pcba.step"))
    export_glb(pcb_path, glb_file=cad_path.joinpath("pcba.glb"))
    export_dxf(pcb_path, dxf_file=cad_path.joinpath("pcba.dxf"))
    export_gerber(pcb_path, gerber_zip_file=out.joinpath("gerber.zip"))
    pnp_file = out.joinpath("pick_and_place.csv")
    export_pick_and_place(pcb_path, pick_and_place_file=pnp_file)
    convert_kicad_pick_and_place_to_jlcpcb(
        pnp_file,
        out.joinpath("jlcpcb_pick_and_place.csv"),
    )
