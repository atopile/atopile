# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import networkx as nx
from dataclasses import dataclass
from faebryk.libs.util import hashable_dict
from faebryk.libs.exceptions import FaebrykException

# 0. netlist = graph

#TODO add name precendence
# t1 is basically a reduced version of the graph
# t1_netlist = [
#     {name, value, properties, real,
#       neighbors={pin: [{&vertex, pin}]},
# ]

def _make_graph(netlist):
    class _Vertex(hashable_dict):
        def __init__(self, node, pin):
            super().__init__({"node": node["name"], "pin": pin})
            self.node = node
            self.pin = pin

    G = nx.Graph()
    edges = [(
                _Vertex(node, source_pin),
                _Vertex(neighbor["vertex"], neighbor["pin"])
        )
        for node in netlist
        for source_pin, neighbors in node.get("neighbors", {1: []}).items()
        for neighbor in neighbors
    ]
    for source_vertex, dest_vertex in edges:
        if dest_vertex.node not in netlist:
            raise FaebrykException("Referenced node not in netlist: {}".format(
                dest_vertex.node["name"]))

    G.add_edges_from(edges)
    return G

@dataclass(frozen=True)
class Component:
    name: str
    value: 'typing.Any'
    properties: dict

@dataclass(frozen=True)
class Vertex:
    component: Component
    pin: int

@dataclass(frozen=True)
class Net:
    properties: dict
    vertices: list[Vertex]

def make_t2_netlist_from_t1(t1_netlist):
    # make undirected graph where nodes=(vertex, pin),
    #   edges=in neighbors relation
    # nets = connected components
    # opt: determine net.prop.name by nodes?

    G = _make_graph(t1_netlist)
    nets = list(nx.connected_components(G))

    # Only keep nets that have more than one real component connected
    nets = [net for net in nets
        if len([vertex for vertex in net if vertex.node["real"]]) > 1]

    def determine_net_name(net):
        #TODO use name precedence instead

        virtual_name = "-".join(
            [
                vertex.node["name"] + ("" if vertex.pin == 1 else f":{vertex.pin}")
                    for vertex in net
                    if not vertex.node["real"]
            ])
        if virtual_name != "":
            return virtual_name

        comp_name = "-".join(vertex.node["name"] for vertex in net)
        if comp_name != "":
            return comp_name

        #TODO implement default policy
        raise NotImplementedError

    t2_netlist = [
        Net(
            properties = {
                "name": determine_net_name(net),
            },
            vertices = [
                Vertex(
                    component = Component(
                        name = vertex.node["name"],
                        value = vertex.node["value"],
                        properties = vertex.node["properties"],
                    ),
                    pin = vertex.pin,
                )
                for vertex in net
                if vertex.node["real"]
            ]
        )
        for net in nets
    ]

    return t2_netlist

def render_graph(t1_netlist):
    import matplotlib.pyplot as plt

    G = _make_graph(t1_netlist)

    netedges = G.edges()

    comp_edges = [
        (vertex.node["name"], vertex)
        for vertex in G.nodes
    ]
    G.add_edges_from(comp_edges)

    def vertex_name(vertex):
        if isinstance(vertex, str):
            return vertex
        return str(vertex.pin)
    vertex_names = {
        vertex : vertex_name(vertex)
        for vertex in G.nodes
    }

    plt.subplot(121)
    layout = nx.spring_layout(G)
    #nx.draw_networkx_nodes(G, pos=layout)
    nx.draw_networkx_edges(G, pos=layout, edgelist=netedges, edge_color="#FF0000")
    nx.draw_networkx_edges(G, pos=layout, edgelist=comp_edges, edge_color="#0000FF")
    nx.draw_networkx_labels(G, pos=layout, labels=vertex_names)
    plt.show()
