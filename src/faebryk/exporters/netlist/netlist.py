# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import faebryk.library._F as F
from faebryk.core.graphinterface import Graph

logger = logging.getLogger(__name__)


@dataclass
class T2Netlist:
    @dataclass(frozen=True)
    class Component:
        name: str
        value: str
        properties: dict[str, str]

        def __hash__(self) -> int:
            return hash((self.name, self.value, self.properties["footprint"]))

    @dataclass(frozen=True)
    class Net:
        @dataclass(frozen=True)
        class Vertex:
            component: "T2Netlist.Component"
            pin: str

        properties: dict[str, str]
        vertices: list[Vertex]

    nets: list[Net]
    comps: list[Component]


def make_t2_netlist_from_graph(G: Graph) -> T2Netlist:
    from faebryk.core.util import get_all_nodes_of_type, get_all_nodes_with_trait
    from faebryk.exporters.netlist.graph import can_represent_kicad_footprint
    from faebryk.library.Net import Net as FNet

    nets = get_all_nodes_of_type(G, FNet)

    t2_nets = [
        T2Netlist.Net(
            properties={"name": net.get_trait(F.has_overriden_name).get_name()},
            vertices=sorted(
                [
                    T2Netlist.Net.Vertex(
                        component=t.get_kicad_obj(),
                        pin=t.get_pin_name(mif),
                    )
                    for mif, fp in net.get_fps().items()
                    if (t := fp.get_trait(can_represent_kicad_footprint)) is not None
                ],
                key=lambda v: (v.component.name, v.pin),
            ),
        )
        for net in nets
    ]

    comps = {
        t.get_footprint().get_trait(can_represent_kicad_footprint).get_kicad_obj()
        for _, t in get_all_nodes_with_trait(G, F.has_footprint)
    }

    not_found = [
        vertex.component
        for net in t2_nets
        for vertex in net.vertices
        if vertex.component.name not in {c.name for c in comps}
    ]
    assert not not_found, f"Could not match: {not_found}"

    return T2Netlist(nets=t2_nets, comps=list(comps))
