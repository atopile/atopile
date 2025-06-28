# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions

logger = logging.getLogger(__name__)


@dataclass
class FBRKNetlist:
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
            component: "FBRKNetlist.Component"
            pin: str

        properties: dict[str, str]
        vertices: list[Vertex]

    nets: list[Net]
    comps: list[Component]


def make_fbrk_netlist_from_graph(G: Graph) -> FBRKNetlist:
    from faebryk.exporters.netlist.graph import can_represent_kicad_footprint

    nets = GraphFunctions(G).nodes_of_type(F.Net)
    # all buses have at least one net with name at this point
    named_nets = {n for n in nets if n.has_trait(F.has_overriden_name)}

    fbrk_nets = [
        FBRKNetlist.Net(
            properties={"name": net.get_trait(F.has_overriden_name).get_name()},
            vertices=sorted(
                [
                    FBRKNetlist.Net.Vertex(
                        component=t.get_kicad_obj(),
                        pin=t.get_pin_name(mif),
                    )
                    for mif, fp in net.get_connected_pads().items()
                    if (t := fp.get_trait(can_represent_kicad_footprint)) is not None
                ],
                key=lambda v: (v.component.name, v.pin),
            ),
        )
        for net in named_nets
    ]

    comps = {
        t.get_footprint().get_trait(can_represent_kicad_footprint).get_kicad_obj()
        for _, t in GraphFunctions(G).nodes_with_trait(F.has_footprint)
    }

    not_found = [
        vertex.component
        for net in fbrk_nets
        for vertex in net.vertices
        if vertex.component.name not in {c.name for c in comps}
    ]
    assert not not_found, f"Could not match: {not_found}"

    return FBRKNetlist(nets=fbrk_nets, comps=list(comps))
