# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import shutil
from pathlib import Path

import faebryk.libs.picker.lcsc as lcsc
from faebryk.core.core import Module
from faebryk.core.graph import Graph
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.visualize.graph import render_sidebyside
from faebryk.libs.app.erc import simple_erc
from faebryk.libs.app.kicad_netlist import write_netlist
from faebryk.libs.app.parameters import replace_tbd_with_any
from faebryk.libs.app.pcb import apply_layouts, apply_routing
from faebryk.libs.experiments.pickers import pick_parts_for_examples
from faebryk.libs.kicad.pcb import PCB
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

logger = logging.getLogger(__name__)


def tag_and_export_module_to_netlist(m: Module, pcb_transform: bool = False):
    """
    Picks parts for the module.
    Runs a simple ERC.
    Tags the graph with kicad info.
    Exports the graph to a netlist.
    And writes it to ./build
    """

    logger.info("Filling unspecified parameters")
    # import faebryk.libs.app.parameters as p_mod

    # lvl = p_mod.logger.getEffectiveLevel()
    # p_mod.logger.setLevel(logging.DEBUG)
    replace_tbd_with_any(m, recursive=True)
    # p_mod.logger.setLevel(lvl)

    pick_part_recursively(m, pick_parts_for_examples)
    G = m.get_graph()
    simple_erc(G)
    tag_and_export_graph_to_netlist(G)

    if not pcb_transform:
        return

    export_pcb(m, G)
    return


def tag_and_export_graph_to_netlist(G: Graph):
    NETLIST_OUT.unlink(missing_ok=True)
    return write_netlist(G, NETLIST_OUT, use_kicad_designators=True)


def export_netlist(netlist):
    NETLIST_OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    logging.info("Writing Experiment netlist to {}".format(NETLIST_OUT.absolute()))
    NETLIST_OUT.write_text(netlist)


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


def export_pcb(app: Module, G: Graph):
    example_prj = Path(__file__).parent / Path("resources/example")

    PCB_FILE.unlink(missing_ok=True)

    shutil.copytree(example_prj, KICAD_SRC, dirs_exist_ok=True)

    print(
        "Open the PCB in kicad and import the netlist.\n"
        "Then save the pcb and press ENTER.\n"
        f"PCB location: {PCB_FILE}"
    )
    input()

    logger.info("Load PCB")
    pcb = PCB.load(PCB_FILE)

    transformer = PCB_Transformer(pcb, G, app)

    logger.info("Transform PCB")

    # set layout
    apply_layouts(app)
    transformer.move_footprints()
    apply_routing(app, transformer)

    logger.info(f"Writing pcbfile {PCB_FILE}")
    pcb.dump(PCB_FILE)

    print("Reopen PCB in kicad")
