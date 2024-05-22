# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.exporters.netlist.netlist import Component, Net, Vertex
from faebryk.libs.kicad.parser import parse_kicad_netlist


def to_faebryk_t2_netlist(kicad_netlist):
    # t2_netlist = [(properties, vertices=[(comp=(name, value, properties), pin)])]

    # kicad_netlist = {
    #   comps:  [(ref, value, fp, tstamp)],
    #   nets:   [(code, name, [node=(ref, pin)])],
    # }

    netlist = parse_kicad_netlist(kicad_netlist)

    components: dict[str, Component] = {
        comp["ref"]: Component(
            name=comp["ref"],
            value=comp["value"],
            properties={"footprint": comp["footprint"]} | comp.get("properties", {}),
        )
        for comp in netlist["components"].values()
    }

    t2_netlist = {
        "nets": [
            Net(
                properties={
                    "name": net["name"],
                },
                vertices=[
                    Vertex(
                        component=components[node["ref"]],
                        pin=node["pin"],
                    )
                    for node in net["nodes"]
                ],
            )
            for net in netlist["nets"].values()
        ],
        "comps": list(components.values()),
    }

    return t2_netlist
