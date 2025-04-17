# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from pathlib import Path

from faebryk.exporters.netlist.netlist import FBRKNetlist
from faebryk.libs.kicad.fileformats_latest import C_kicad_netlist_file


def to_faebryk_t2_netlist(kicad_netlist: str | Path | list) -> FBRKNetlist:
    netlist = C_kicad_netlist_file.loads(kicad_netlist)

    components: dict[str, FBRKNetlist.Component] = {
        comp.ref: FBRKNetlist.Component(
            name=comp.ref,
            value=comp.value,
            properties={"footprint": comp.footprint}
            | {v.name: v.value for v in comp.propertys.values()},
        )
        for comp in netlist.export.components.comps
    }

    t2_netlist = FBRKNetlist(
        nets=[
            FBRKNetlist.Net(
                properties={
                    "name": net.name,
                },
                vertices=[
                    FBRKNetlist.Net.Vertex(
                        component=components[node.ref],
                        pin=node.pin,
                    )
                    for node in net.nodes
                ],
            )
            for net in netlist.export.nets.nets
        ],
        comps=list(components.values()),
    )

    return t2_netlist
