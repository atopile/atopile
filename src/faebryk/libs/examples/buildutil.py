# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import shutil
from pathlib import Path
from typing import Callable

import faebryk.libs.picker.lcsc as lcsc
from atopile.config import BuildPaths
from faebryk.core.module import Module
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.libs.app.checks import run_checks
from faebryk.libs.app.parameters import replace_tbd_with_any, resolve_dynamic_parameters
from faebryk.libs.app.pcb import apply_design
from faebryk.libs.examples.pickers import add_example_pickers
from faebryk.libs.picker.api.api import ApiNotConfiguredError
from faebryk.libs.picker.api.pickers import add_api_pickers
from faebryk.libs.picker.common import DB_PICKER_BACKEND, CachePicker, PickerType
from faebryk.libs.picker.jlcpcb.jlcpcb import JLCPCB_DB
from faebryk.libs.picker.jlcpcb.pickers import add_jlcpcb_pickers
from faebryk.libs.picker.picker import pick_part_recursively
from faebryk.libs.util import ConfigFlag

NAME = "example"
BUILD_DIR = Path("./build")
KICAD_SRC = BUILD_DIR / "kicad" / "source"


build_paths: BuildPaths = BuildPaths(
    root=Path("."),
    layout=KICAD_SRC / f"{NAME}.kicad_pcb",
    lock_file=None,
    build=BUILD_DIR,
    output_base=BUILD_DIR / NAME,
    netlist=BUILD_DIR / "faebryk" / "faebryk.net",
    fp_lib_table=KICAD_SRC / "fp-lib-table",
    component_lib=BUILD_DIR / "footprints",
    kicad_project=KICAD_SRC / f"{NAME}.kicad_pro",
)


lcsc.BUILD_FOLDER = build_paths.build
lcsc.LIB_FOLDER = build_paths.component_lib
lcsc.MODEL_PATH = None


DEV_MODE = ConfigFlag("EXP_DEV_MODE", False)

logger = logging.getLogger(__name__)


def apply_design_to_pcb(
    m: Module, transform: Callable[[PCB_Transformer], None] | None = None
):
    """
    Picks parts for the module.
    Runs a simple ERC.
    Tags the graph with kicad info.
    Exports the graph to a netlist.
    Writes it to ./build
    Opens PCB and applies design (netlist, layout, route, ...)
    Saves PCB
    """

    logger.info("Filling unspecified parameters")

    replace_tbd_with_any(
        m, recursive=True, loglvl=logging.DEBUG if DEV_MODE else logging.INFO
    )

    G = m.get_graph()
    resolve_dynamic_parameters(G)
    run_checks(m, G)

    # TODO this can be prettier
    # picking ----------------------------------------------------------------
    modules = m.get_children_modules(types=Module)
    CachePicker.add_to_modules(modules, prio=-20)

    match DB_PICKER_BACKEND:
        case PickerType.SQLITE:
            try:
                JLCPCB_DB()
                for n in modules:
                    add_jlcpcb_pickers(n, base_prio=-10)
            except FileNotFoundError:
                logger.warning("JLCPCB database not found. Skipping JLCPCB pickers.")
        case PickerType.API:
            try:
                for n in modules:
                    add_api_pickers(n)
            except ApiNotConfiguredError:
                logger.warning("API not configured. Skipping API pickers.")

    for n in modules:
        add_example_pickers(n)
    pick_part_recursively(m)
    # -------------------------------------------------------------------------

    example_prj = Path(__file__).parent / Path("resources/example")

    if not DEV_MODE:
        build_paths.netlist.unlink(missing_ok=True)

    if not DEV_MODE or not KICAD_SRC.exists():
        build_paths.layout.unlink(missing_ok=True)
        shutil.copytree(example_prj, KICAD_SRC, dirs_exist_ok=True)

    apply_design(build_paths, m, G, transform)

    return G


def export_graph(g, show):
    raise NotImplementedError()
