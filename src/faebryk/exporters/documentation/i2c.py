# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import faebryk.library._F as F
from faebryk.core.graph import GraphFunctions
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.solver.solver import Solver
from faebryk.libs.util import DAG, groupby, partition_as_list

logger = logging.getLogger(__name__)


def export_i2c_tree(
    app: Module, solver: Solver, path: Path = Path("build/documentation/i2c_tree.md")
):
    """
    Export the I2C tree of the given application to a file.
    """

    # Filter buses
    mifs = GraphFunctions(app.get_graph()).nodes_of_type(F.I2C)
    buses = ModuleInterface._group_into_buses(mifs)
    buses = {
        k: v for k, v in buses.items() if len(v) > 1 and k.bus_crosses_pad_boundary()
    }
    buses_with_address = [
        {
            mif: lit
            for mif in bus
            if (
                lit := solver.inspect_get_known_supersets(mif.address)
            ).is_single_element()
        }
        for bus in buses.values()
    ]

    # Build DAG
    dag = DAG[F.I2C]()
    for bus in buses_with_address:
        clients, servers = partition_as_list(lambda x: x[1] == 0, bus.items())
        for client in clients:
            client_mif, _ = client
            for server in servers:
                server_mif, _ = server
                dag.add_edge(server_mif, client_mif)

    grouped_by_parent = groupby(
        dag.values, lambda x: p[0] if (p := x.get_parent()) is not None else None
    )

    # Make a mermaid diagram from the dag
    out = "graph TD\n"
    node_names = {}
    i = 0
    # Build nodes
    for container, mifs in grouped_by_parent.items():
        if len(mifs) > 1 and container is not None:
            out += f"    subgraph {container.get_full_name()}\n"
        for mif in mifs:
            node_name = f"node_{i}"
            node_names[mif] = node_name
            address = solver.inspect_get_known_supersets(mif.address)

            label = f"{mif.get_full_name()}"
            is_server = address == 0

            if is_server:
                out += f'    {node_name}("{label}")\n'
            else:
                address_str = hex(int(address.any().m))
                label += f"<br/>{address_str}"
                out += f'    {node_name}(("{label}"))\n'

            i += 1

        if len(mifs) > 1 and container is not None:
            out += "    end\n"

    # Build edges
    for parent_value in dag.values:
        parent_internal_node = dag.get(parent_value)
        parent_node_name = node_names[parent_value]
        for child_internal_node in parent_internal_node._children:
            child_value = child_internal_node.value
            child_node_name = node_names[child_value]
            out += f"    {parent_node_name} --> {child_node_name}\n"

    # Write to file
    path.parent.mkdir(parents=True, exist_ok=True)
    markdown = "```mermaid\n" + out + "```"
    path.write_text(markdown, encoding="utf-8")
    logger.info(f"Wrote I2C tree to {path}")
