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

    components = {
        comp["ref"]: Component(
            name=comp["ref"],
            value=comp["value"],
            properties={"footprint": comp["footprint"]},
        )
        for comp in netlist["components"].values()
    }

    t2_netlist = [
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
    ]

    return t2_netlist


def to_faebryk_t1_netlist_simple(t2_netlist):
    # t1_netlist = [
    #     {name, value, properties, real,
    #       neighbors={pin: [{&vertex, pin}]},
    # ]

    def comp2v(comp, neigh):
        return {
            "name": comp.name,
            "real": True,
            "properties": {"footprint": comp.properties["footprint"]},
            "neighbors": neigh,
            "value": comp.value,
        }

    def ncomp2v(comp, comps):
        comp["neighbors"] = {
            pin: [{"vertex": comps[v.component.name], "pin": v.pin} for v in neigh]
            for pin, neigh in comp["neighbors"].items()
        }
        return comp

    comp_neighbours = {
        vertex.component.name: (vertex.component, {})
        for net in t2_netlist
        for vertex in net.vertices
    }

    for net in t2_netlist:
        for vertex in net.vertices:
            comp_neighbours[vertex.component.name][1][vertex.pin] = [
                v for v in net.vertices if v is not vertex
            ]

    pre = {name: comp2v(comp, neigh) for name, (comp, neigh) in comp_neighbours.items()}

    t1_netlist = [ncomp2v(comp, pre) for comp in pre.values()]

    return t1_netlist


def to_faebryk_t1_netlist(t2_netlist):
    # t1_netlist = [
    #     {name, value, properties, real,
    #       neighbors={pin: [{&vertex, pin}]},
    # ]

    nets = []
    for net in t2_netlist:
        if len(net.vertices) > 2:
            virtual = Component(
                name=net.properties["name"],
                value=None,
                properties={},
            )
            for vertex in net.vertices:
                nets.append(
                    Net(
                        properties={"name": f"{virtual.name}-{vertex.component.name}"},
                        vertices=[
                            Vertex(
                                component=vertex.component,
                                pin=vertex.pin,
                            ),
                            Vertex(
                                component=virtual,
                                pin="1",
                            ),
                        ],
                    )
                )
        elif len(net.vertices) == 2:
            nets.append(net)

    def comp2v(comp, neigh):
        return {
            "name": comp.name,
            "real": "footprint" in comp.properties,
            "properties": comp.properties,
            "neighbors": neigh,
            "value": comp.value,
        }

    def ncomp2v(comp, comps):
        comp["neighbors"] = {
            pin: [{"vertex": comps[v.component.name], "pin": v.pin} for v in neigh]
            for pin, neigh in comp["neighbors"].items()
        }
        return comp

    comp_neighbours = {
        vertex.component.name: (vertex.component, {})
        for net in nets
        for vertex in net.vertices
    }

    for net in nets:
        for vertex in net.vertices:
            comp_neighbours[vertex.component.name][1][vertex.pin] = [
                v for v in net.vertices if v.component.name != vertex.component.name
            ]

    pre = {name: comp2v(comp, neigh) for name, (comp, neigh) in comp_neighbours.items()}

    t1_netlist = [ncomp2v(comp, pre) for comp in pre.values()]

    return t1_netlist
