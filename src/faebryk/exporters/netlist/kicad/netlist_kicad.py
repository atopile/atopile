# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import itertools
import logging

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.exporters.netlist.graph import can_represent_kicad_footprint
from faebryk.exporters.netlist.netlist import FBRKNetlist
from faebryk.libs.kicad.fileformats_latest import C_fields, C_kicad_netlist_file
from faebryk.libs.util import duplicates

logger = logging.getLogger(__name__)


def faebryk_netlist_to_kicad(fbrk_netlist: FBRKNetlist):
    tstamp = itertools.count(1)
    net_code = itertools.count(1)

    # KiCAD Constraints:
    #   - name has to be unique
    #   - vertex properties has to contain footprint
    #   - tstamps can be generated (unique)
    #   - net_code can be generated (ascending, continuous)
    #   - components unique

    dupes = duplicates(fbrk_netlist.comps, lambda comp: comp.name)
    assert not dupes, f"Duplicate comps {dupes}"

    NetlistFile = C_kicad_netlist_file
    Component = NetlistFile.C_netlist.C_components.C_component
    comps = [
        Component(
            ref=comp.name,
            value=comp.value,
            footprint=comp.properties["footprint"],
            propertys={
                k: Component.C_property(k, v)
                for k, v in comp.properties.items()
                if k != "footprint"
            },
            tstamps=str(next(tstamp)),
            fields=C_fields(
                {
                    k: C_fields.C_field(k, v)
                    for k, v in comp.properties.get("fields", [])
                }
            ),
        )
        # sort because tstamp determined by pos
        for comp in sorted(fbrk_netlist.comps, key=lambda comp: comp.name)
    ]

    # check if all vertices have a component in pre_comps
    # not sure if this is necessary
    pre_comp_names = {comp.name for comp in fbrk_netlist.comps}
    for net in fbrk_netlist.nets:
        for vertex in net.vertices:
            assert vertex.component.name in pre_comp_names, (
                f"Missing {vertex.component}"
            )

    Net = NetlistFile.C_netlist.C_nets.C_net
    nets = [
        Net(
            code=next(net_code),
            name=net.properties["name"],
            nodes=[
                Net.C_node(
                    ref=vertex.component.name,
                    pin=vertex.pin,
                )
                for vertex in sorted(net.vertices, key=lambda vert: vert.component.name)
            ],
        )
        # sort because code determined by pos
        for net in sorted(fbrk_netlist.nets, key=lambda net: net.properties["name"])
    ]

    return NetlistFile(
        export=NetlistFile.C_netlist(
            version="E",
            components=NetlistFile.C_netlist.C_components(comps=comps),
            nets=NetlistFile.C_netlist.C_nets(nets=nets),
        )
    )


def attach_kicad_info(G: Graph) -> None:
    """Attach kicad info to the footprints in the graph."""
    # group comps & fps
    node_fps = {
        n: t.get_footprint()
        # TODO maybe nicer to just look for footprints
        # and get their respective components instead
        for n, t in GraphFunctions(G).nodes_with_trait(F.has_footprint)
        if isinstance(n, Module)
    }

    logger.info(f"Found {len(node_fps)} components with footprints")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"node_fps: {node_fps}")

    # add trait/info to footprints
    for n, fp in node_fps.items():
        if fp.has_trait(can_represent_kicad_footprint):
            continue
        fp.add(can_represent_kicad_footprint(n, G))
