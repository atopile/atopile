# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("netlist")

import typing
from dataclasses import dataclass

import networkx as nx

from faebryk.libs.exceptions import FaebrykException
from faebryk.libs.util import NotNone, hashable_dict, unique

# 0. netlist = graph

# TODO add name precendence
# t1 is basically a reduced version of the graph
# t1_netlist = [
#     {name, value, properties, real,
#       neighbors={pin: [{&vertex, pin}]},
# ]


@dataclass(frozen=True)
class Component:
    name: str
    value: "typing.Any"
    properties: dict


@dataclass(frozen=True)
class Vertex:
    component: Component
    pin: str


@dataclass(frozen=True)
class Net:
    properties: dict
    vertices: list[Vertex]


class _GraphVertex(hashable_dict):
    # node is t1_netlist node
    def __init__(self, node: dict, pin: int):
        super().__init__({"node": node["name"], "pin": pin})
        self.node = node
        self.pin = pin


# netlist = t1_netlist
def _make_graph(netlist):
    G = nx.Graph()
    edges = [
        (
            _GraphVertex(node, source_pin),
            _GraphVertex(neighbor["vertex"], neighbor["pin"]),
        )
        for node in netlist
        for source_pin, neighbors in node.get("neighbors", {1: []}).items()
        for neighbor in neighbors
    ]
    for source_vertex, dest_vertex in edges:
        if dest_vertex.node not in netlist:
            for c in netlist:
                if c["name"] == dest_vertex.node["name"]:
                    logger.debug(f"{c} != {dest_vertex.node}")
            raise FaebrykException(
                "{} was connected to but not in graph as node".format(
                    dest_vertex.node["name"]
                )
            )
    # TODO check if any nodes in netlist are not appearing in Graph

    G.add_edges_from(edges)
    return G


def make_t2_netlist_from_t1(t1_netlist):
    # make undirected graph where nodes=(vertex, pin),
    #   edges=in neighbors relation
    # nets = connected components
    # opt: determine net.prop.name by nodes?

    G = _make_graph(t1_netlist)
    nets = list(nx.connected_components(G))

    # Only keep nets that have more than one real component connected
    nets = [
        net
        for net in nets
        if len([vertex for vertex in net if vertex.node["real"]]) > 1
    ]

    def determine_net_name(net):
        # TODO use name precedence instead

        virtual_name = "-".join(
            [
                vertex.node["name"] + ("" if vertex.pin == 1 else f":{vertex.pin}")
                for vertex in net
                if not vertex.node["real"]
            ]
        )
        if virtual_name != "":
            return virtual_name

        comp_name = "-".join(vertex.node["name"] for vertex in net)
        if comp_name != "":
            return comp_name

        # TODO implement default policy
        raise NotImplementedError

    t2_netlist = [
        Net(
            properties={
                "name": determine_net_name(net),
            },
            vertices=[
                Vertex(
                    component=Component(
                        name=vertex.node["name"],
                        value=vertex.node["value"],
                        properties=vertex.node["properties"],
                    ),
                    pin=vertex.pin,
                )
                for vertex in net
                if vertex.node["real"]
            ],
        )
        for net in nets
    ]

    return t2_netlist


def render_graph(t1_netlist):
    import matplotlib.pyplot as plt

    G = _make_graph(t1_netlist)

    netedges = G.edges()

    # Make edges between pins within component
    def _get_vertex_pins(vertex):
        return list(vertex.node["neighbors"].keys())

    nodes: typing.List[_GraphVertex] = list(G.nodes)
    intra_comp_edges = [
        (_GraphVertex(vertex.node, spin), _GraphVertex(vertex.node, dpin))
        for vertex in nodes
        for spin in _get_vertex_pins(vertex)
        for dpin in _get_vertex_pins(vertex)
        if spin != dpin
    ]
    G.add_edges_from(intra_comp_edges)

    # TODO why the isinstance?
    def vertex_name(vertex):
        if isinstance(vertex, str):
            return vertex
        return str(vertex.pin)

    vertex_names = {vertex: vertex_name(vertex) for vertex in G.nodes}

    import re

    # (match.group() if (match:=re.search(r"\[.*\]", edge[0].node["name"])) is not None else None)

    intra_edge_dict = dict(
        unique(
            {
                edge: "{}".format(
                    NotNone(re.search(r"\[.*\]", edge[0].node["name"])).group()
                    if edge[0].node["name"].startswith("COMP[")
                    else edge[0].node["name"]
                )
                for edge in intra_comp_edges
            }.items(),
            key=lambda edge: edge[0][0].node,
        )
    )

    # Draw
    plt.subplot(121)
    layout = nx.spring_layout(G)
    nx.draw_networkx_nodes(G, pos=layout, node_size=150)
    nx.draw_networkx_edges(G, pos=layout, edgelist=netedges, edge_color="#FF0000")
    nx.draw_networkx_edges(
        G, pos=layout, edgelist=intra_comp_edges, edge_color="#0000FF"
    )
    nx.draw_networkx_labels(G, pos=layout, labels=vertex_names)
    nx.draw_networkx_edge_labels(
        G,
        pos=layout,
        edge_labels=intra_edge_dict,
        font_size=10,
        rotate=False,
        bbox=dict(fc="blue"),
        font_color="white",
    )

    return plt
