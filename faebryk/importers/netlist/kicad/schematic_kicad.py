# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.exporters.netlist.netlist import Component, Net, Vertex
from faebryk.libs.algorithm import ufds
from faebryk.libs.kicad.parser import parse_kicad_schematic
from faebryk.libs.util import flatten, get_dict


def to_faebryk_t2_netlist(kicad_schematic, file_loader=None):
    # t2_netlist = [(properties, vertices=[(comp=(name, value, properties), pin)])]

    # kicad_netlist = {
    #   comps:  [(ref, value, fp, tstamp)],
    #   nets:   [(code, name, [node=(ref, pin)])],
    # }

    # TODO
    # buses
    # labels
    # power symbols
    # warn: no fp symbols
    # sheets

    schematic = parse_kicad_schematic(kicad_schematic, file_loader=file_loader)

    import pprint

    # pprint.pprint(schematic, indent=4)
    from pathlib import Path

    path = Path("./build/faebryk_sch")
    path.write_text(pprint.pformat(schematic, indent=4))
    # -------------------------------------------------------------------------
    def load_sheet_nets(sheet_schematic):
        def subname_to_tpl(subname: str):
            split = subname.split("_")
            return split[-2], split[-1]

        pins = {
            # lib_name: pins
            name: {
                # modname: pins
                subname_to_tpl(subname): subsym.get("pins", {})
                for subname, subsym in lib_sym["symbols"].items()
            }
            for name, lib_sym in sheet_schematic["lib_symbols"].items()
        }

        print("-" * 80)
        print("pins")
        pprint.pprint(pins, indent=4)
        # -------------------------------------------------------------------------

        def get_pins(ref, sym, subsym, unit):
            convert = subsym.get("convert", 1)
            lib_name = subsym["lib_id"]
            base_coord = subsym["at"]
            mirror = subsym.get("mirror", None)
            # symbol coordinate system has inverted y-axis to sch coord system??
            mirror_vec = (
                (1, -1)
                if mirror is None
                else (-1, -1)
                if mirror == "x"
                else (1, 1)
                if mirror == "y"
                else None
            )
            assert mirror_vec is not None

            obj = {
                "ref": ref,
                "lib_name": lib_name,
                "unit": subsym["unit"],
            }

            raw_pins = {}

            for u in ["0", str(unit)]:
                for c in ["0", str(convert)]:
                    raw_pins.update(pins[lib_name].get((u, c), {}))

            def translate_pin(pin):
                out = dict(pin)
                x, y = pin["at"]
                x, y = mirror_vec[0] * x, mirror_vec[1] * y

                import math

                angle = -base_coord[2] / 360 * 2 * math.pi
                cos = math.cos(angle)
                sin = math.sin(angle)
                rx, ry = x * cos - y * sin, x * sin + y * cos
                out["at"] = (round(rx + base_coord[0], 2), round(ry + base_coord[1], 2))
                return out

            translated_pins = {
                pin_name: translate_pin(pin) for pin_name, pin in raw_pins.items()
            }

            obj["pins"] = translated_pins

            return obj

        sym_pins = [
            get_pins(ref, sym, subsym, unit)
            for ref, sym in sheet_schematic["symbols"].items()
            for unit, subsym in sym.items()
            if subsym["properties"]["Footprint"] != ""
        ]

        print("-" * 80)
        print("sym_pins")
        pprint.pprint(sym_pins, indent=4)
        # -------------------------------------------------------------------------
        components = {
            (ref := sym_pin["ref"]): Component(
                name=ref,
                value=(
                    symbol := sheet_schematic["symbols"][sym_pin["ref"]][
                        sym_pin["unit"]
                    ]
                )["properties"]["Value"],
                properties={"footprint": symbol["properties"]["Footprint"]},
            )
            for sym_pin in sym_pins
        }
        # -------------------------------------------------------------------------

        # organize by coords
        coords = {}
        # coord: [(ref, pin_name, pin)]
        for pins in sym_pins:
            for pin_name, pin in pins["pins"].items():
                coord = pin["at"]
                if coord not in coords:
                    coords[coord] = []
                coords[coord].append(
                    {
                        "ref": pins["ref"],
                        "name": pin_name,
                        "raw_pin": pin,
                        "unit": pins["unit"],
                    }
                )

        print("-" * 80)
        print("coords")
        pprint.pprint(coords, indent=4)
        # -------------------------------------------------------------------------

        nets = []
        label_nets = {"global": {}, "hierarchical": {}}
        for file, sheet in sheet_schematic["sheets"].items():
            print("Load", file)
            sub_nets, sub_components, sub_labels = load_sheet_nets(sheet["schematic"])
            # TODO hierarchical labels

            # refs are unique across sheets, so this is ok
            components.update(sub_components)

            for name, sub_label_nets in sub_labels["global"].items():
                if name in sheet_schematic["labels"]:
                    get_dict(
                        coords, sheet_schematic["labels"][name][0]["coord"], list
                    ).extend(sub_label_nets)
                else:
                    get_dict(label_nets["global"], name, list).extend(sub_label_nets)

            nets += sub_nets
        # -------------------------------------------------------------------------

        bridges = []

        # find labels on wires (non-ends)
        for name, labels in sheet_schematic["labels"].items():
            for label in labels:
                lpt = label["coord"]
                for wire in sheet_schematic["wires"]:
                    pts = wire["points"]

                    if lpt in pts:
                        # print("Wire at end", label, wire)
                        continue

                    if lpt[0] < min(pts[1][0], pts[0][0]) or lpt[0] > max(
                        pts[1][0], pts[0][0]
                    ):
                        continue

                    # a = (pts[1][1]-pts[0][1])/(pts[1][0]-pts[0][0]) #dy/dx
                    # matches = (lpt[0]-pts[0][0])*a + pts[0][1] == lpt[1]
                    # matches = (lpt[0]-pts[0][0])*a == lpt[1] - pts[0][1]
                    # matches = (lpt[0]-pts[0][0])*(pts[1][1]-pts[0][1])/(pts[1][0]-pts[0][0]) == lpt[1] - pts[0][1]
                    # matches = (lpt[0]-pts[0][0])*(pts[1][1]-pts[0][1]) == (lpt[1] - pts[0][1]) * (pts[1][0]-pts[0][0])
                    matches = round(
                        (lpt[0] - pts[0][0]) * (pts[1][1] - pts[0][1]), 2
                    ) == round((lpt[1] - pts[0][1]) * (pts[1][0] - pts[0][0]), 2)

                    if matches:
                        bridges.append([lpt, pts[0]])
                        # print("Found", label, "on", wire)

        bridges += [wire["points"] for wire in sheet_schematic["wires"]]
        # TODO ignore/handle buslabels
        bridges += [
            [label["coord"] for label in labels]
            for name, labels in sheet_schematic["labels"].items()
        ]

        # TODO labels on wires

        # create the extra coords for the set
        for coord in flatten(bridges):
            if coord in coords:
                continue
            coords[coord] = []

        # print(coords.keys())

        union = ufds()
        union.make_set(coords.keys())

        # bridge union
        for bridge in bridges:
            for coord in bridge:
                union.op_union(bridge[0], coord)

        merged = {}
        for coord, cpins in coords.items():
            ptr = union.op_find(coord)
            if ptr not in merged:
                merged[ptr] = []
            merged[ptr] += cpins

        print("-" * 80)
        print("merged")
        pprint.pprint(merged, indent=4)

        nets += [net for net in merged.values() if len(net) > 0]
        # -------------------------------------------------------------------------
        for name, labels in sheet_schematic["labels"].items():
            for label in labels:
                if label["type"] == "local":
                    continue
                get_dict(label_nets[label["type"]], name, list).extend(
                    merged[union.op_find(label["coord"])]
                )

        return nets, components, label_nets

    # -------------------------------------------------------------------------
    nets, components, _ = load_sheet_nets(schematic)

    # make netlist from union -------------------------------------------------

    t2_netlist = [
        Net(
            properties={
                "name": "-".join(
                    [f"{net_pin['ref']}:{net_pin['name']}" for net_pin in net_pins]
                ),
            },
            vertices=[
                Vertex(
                    component=components[net_pin["ref"]],
                    pin=net_pin["name"],
                )
                for net_pin in net_pins
            ],
        )
        for net_pins in nets
    ]

    return t2_netlist
