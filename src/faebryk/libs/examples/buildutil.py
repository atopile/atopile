# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import shutil
from pathlib import Path

import faebryk.libs.picker.lcsc as lcsc
from faebryk.core.core import Module
from faebryk.core.util import get_all_modules
from faebryk.exporters.visualize.graph import render_sidebyside
from faebryk.libs.app.checks import run_checks
from faebryk.libs.app.parameters import replace_tbd_with_any
from faebryk.libs.app.pcb import apply_design
from faebryk.libs.examples.pickers import add_example_pickers
from faebryk.libs.picker.jlcpcb.jlcpcb import JLCPCB_DB
from faebryk.libs.picker.jlcpcb.pickers import add_jlcpcb_pickers
from faebryk.libs.picker.picker import pick_part_recursively

BUILD_DIR = Path("./build")
GRAPH_OUT = BUILD_DIR / Path("faebryk/graph.png")
NETLIST_OUT = BUILD_DIR / Path("faebryk/faebryk.net")
KICAD_SRC = BUILD_DIR / Path("kicad/source")
PCB_FILE = KICAD_SRC / Path("example.kicad_pcb")
PROJECT_FILE = KICAD_SRC / Path("example.kicad_pro")

lcsc.BUILD_FOLDER = BUILD_DIR
lcsc.LIB_FOLDER = BUILD_DIR / Path("kicad/libs")
lcsc.MODEL_PATH = None

DEV_MODE = os.environ.get("FBRK_EXP_DEV_MODE", False) in ["y", "Y", "True", "true", "1"]

logger = logging.getLogger(__name__)


def apply_design_to_pcb(m: Module):
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

    # TODO this can be prettier
    # picking ----------------------------------------------------------------
    modules = {n.get_most_special() for n in get_all_modules(m)}
    try:
        JLCPCB_DB()
        for n in modules:
            add_jlcpcb_pickers(n, base_prio=-10)
    except FileNotFoundError:
        logger.warning("JLCPCB database not found. Skipping JLCPCB pickers.")

    for n in modules:
        add_example_pickers(n)
    pick_part_recursively(m)
    # -------------------------------------------------------------------------

    G = m.get_graph()
    run_checks(m, G)

    example_prj = Path(__file__).parent / Path("resources/example")

    if not DEV_MODE:
        NETLIST_OUT.unlink(missing_ok=True)

    if not DEV_MODE or not KICAD_SRC.exists():
        PCB_FILE.unlink(missing_ok=True)
        shutil.copytree(example_prj, KICAD_SRC, dirs_exist_ok=True)

    apply_design(PCB_FILE, NETLIST_OUT, G, m)

    return G


def export_graph(g, show):
    plt = render_sidebyside(g)

    GRAPH_OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    logging.info("Writing Experiment graph to {}".format(GRAPH_OUT.absolute()))
    plt.savefig(GRAPH_OUT, format="png", bbox_inches="tight")

    if show:
        plt.show()
