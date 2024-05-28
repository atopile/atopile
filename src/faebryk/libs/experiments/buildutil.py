# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import faebryk.libs.picker.lcsc as lcsc
from faebryk.core.core import Module
from faebryk.core.graph import Graph
from faebryk.exporters.visualize.graph import render_sidebyside
from faebryk.libs.app.erc import simple_erc
from faebryk.libs.app.kicad_netlist import write_netlist
from faebryk.libs.app.parameters import replace_tbd_with_any
from faebryk.libs.experiments.pickers import pick_parts_for_examples
from faebryk.libs.picker.picker import pick_part_recursively

BUILD_DIR = Path("./build")
GRAPH_OUT = BUILD_DIR / Path("faebryk/graph.png")
NETLIST_OUT = BUILD_DIR / Path("faebryk/faebryk.net")

lcsc.BUILD_FOLDER = BUILD_DIR
lcsc.LIB_FOLDER = BUILD_DIR / Path("kicad/libs")
lcsc.MODEL_PATH = None

logger = logging.getLogger(__name__)


def tag_and_export_module_to_netlist(m: Module):
    """
    Picks parts for the module.
    Runs a simple ERC.
    Tags the graph with kicad info.
    Exports the graph to a netlist.
    And writes it to ./build
    """

    logger.info("Filling unspecified parameters")
    import faebryk.libs.app.parameters as p_mod

    lvl = p_mod.logger.getEffectiveLevel()
    p_mod.logger.setLevel(logging.DEBUG)
    replace_tbd_with_any(m, recursive=True)
    p_mod.logger.setLevel(lvl)

    pick_part_recursively(m, pick_parts_for_examples)
    G = m.get_graph()
    simple_erc(G)
    return tag_and_export_graph_to_netlist(G)


def tag_and_export_graph_to_netlist(G: Graph):
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
