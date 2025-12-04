# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F

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


def make_fbrk_netlist_from_graph(
    g: fabll.graph.GraphView, tg: fbrk.TypeGraph
) -> FBRKNetlist:
    nets = F.Net.bind_typegraph(tg).get_instances()

    named_nets = {n for n in nets if n.has_trait(F.has_overriden_name)}

    named_nets_with_connected_pads = {
        n: n.get_connected_pads() if n.get_parent_of_type(F.Net) else None
        for n in named_nets
    }

    fbrk_nets = [
        FBRKNetlist.Net(
            properties={"name": net.get_trait(F.has_overriden_name).get_name()},
            vertices=sorted(
                [
                    FBRKNetlist.Net.Vertex(
                        component=t.get_kicad_obj(),
                        pin=t.get_pin_name(mif),
                    )
                    for mif, fp in (pads.items() if pads is not None else [])
                    if (t := fp.get_trait(F.can_represent_kicad_footprint))
                ],
                key=lambda v: (v.component.name, v.pin),
            ),
        )
        for net, pads in named_nets_with_connected_pads.items()
    ]

    comps = {
        t.get_trait(F.can_represent_kicad_footprint).get_kicad_obj()
        for t in F.Footprints.GenericFootprint.bind_typegraph(tg).get_instances(g)
        if t.has_trait(F.has_footprint)
    }

    not_found = [
        vertex.component
        for net in fbrk_nets
        for vertex in net.vertices
        if vertex.component.name not in {c.name for c in comps}
    ]
    assert not not_found, f"Could not match: {not_found}"

    return FBRKNetlist(nets=fbrk_nets, comps=list(comps))
