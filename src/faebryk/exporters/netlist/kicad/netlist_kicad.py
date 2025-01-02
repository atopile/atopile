# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import itertools
import logging

from faebryk.exporters.netlist.netlist import FBRKNetlist
from faebryk.libs.kicad.fileformats import C_fields, C_kicad_netlist_file
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
            assert (
                vertex.component.name in pre_comp_names
            ), f"Missing {vertex.component}"

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
