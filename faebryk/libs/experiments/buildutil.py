import logging
from pathlib import Path


def export_netlist(netlist):
    build_folder_path = Path("./build/faebryk/")
    build_folder_path.mkdir(
        parents=True,
        exist_ok=True,
    )
    netlist_filepath = build_folder_path / "faebryk.net"
    logging.info("Writing Experiment netlist to {}".format(netlist_filepath.absolute()))
    netlist_filepath.write_text(netlist)


def export_graph(t1, show):
    from faebryk.exporters.netlist.netlist import render_graph

    plt = render_graph(t1)

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
