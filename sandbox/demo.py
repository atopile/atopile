from pathlib import Path

from atopile import errors
from atopile.datatypes import Ref
from atopile.front_end2 import lofty
from atopile.parse import parse_file

# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import faebryk.libs.picker.lcsc as lcsc
from faebryk.core.module import Module
from faebryk.libs.app.checks import run_checks
from faebryk.libs.app.parameters import resolve_dynamic_parameters
from faebryk.libs.app.pcb import apply_design
from faebryk.libs.picker.api.api import ApiNotConfiguredError
from faebryk.libs.picker.api.pickers import add_api_pickers
from faebryk.libs.picker.common import DB_PICKER_BACKEND, CachePicker, PickerType
from faebryk.libs.picker.jlcpcb.jlcpcb import JLCPCB_DB
from faebryk.libs.picker.jlcpcb.pickers import add_jlcpcb_pickers
from faebryk.libs.picker.picker import pick_part_recursively
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.units import P


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    entry_file_path = Path(__file__).parent / "demo.ato"
    entry_module = Ref(["Main"])

    BUILD_FOLDER = Path(__file__).parent / "build"
    BUILD_FOLDER.mkdir(exist_ok=True)

    lcsc.BUILD_FOLDER = BUILD_FOLDER
    lcsc.LIB_FOLDER = BUILD_FOLDER / "libs"
    lcsc.MODEL_PATH = None  # TODO:

    with errors.log_ato_errors():
        tree = parse_file(entry_file_path)
        m = lofty.build_ast(tree, entry_module)

    assert isinstance(m, Module)

    logger.info("Filling unspecified parameters")

    G = m.get_graph()
    resolve_dynamic_parameters(G)
    run_checks(m, G)

    solver = DefaultSolver()

    # picking ----------------------------------------------------------------
    modules = m.get_children_modules(types=Module)
    CachePicker.add_to_modules(modules, prio=-20)

    match DB_PICKER_BACKEND:
        case PickerType.SQLITE:
            try:
                JLCPCB_DB()
                for n in modules:
                    add_jlcpcb_pickers(n)
            except FileNotFoundError:
                logger.warning("JLCPCB database not found. Skipping JLCPCB pickers.")
        case PickerType.API:
            try:
                for n in modules:
                    add_api_pickers(n)
            except ApiNotConfiguredError:
                logger.warning("API not configured. Skipping API pickers.")

    pick_part_recursively(m, solver)
    solver.find_and_lock_solution(G)
    # -------------------------------------------------------------------------

    netlist_path = lcsc.BUILD_FOLDER / "demo.net"
    pcb_file = Path(__file__).parent / "layout" / "example.kicad_pcb"
    apply_design(pcb_file, netlist_path, G, m, None)  # TODO: transform
