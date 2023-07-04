# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from faebryk.exporters.visualize.graph import render_sidebyside


def export_netlist(netlist):
    build_folder_path = Path("./build/faebryk/")
    build_folder_path.mkdir(
        parents=True,
        exist_ok=True,
    )
    netlist_filepath = build_folder_path / "faebryk.net"
    logging.info("Writing Experiment netlist to {}".format(netlist_filepath.absolute()))
    netlist_filepath.write_text(netlist)


def export_graph(g, show):
    plt = render_sidebyside(g)

    build_folder_path = Path("./build/faebryk/")
    build_folder_path.mkdir(
        parents=True,
        exist_ok=True,
    )
    graph_filepath = build_folder_path / "graph.png"
    logging.info("Writing Experiment graph to {}".format(graph_filepath.absolute()))
    plt.savefig(graph_filepath, format="png", bbox_inches="tight")

    if show:
        plt.show()
