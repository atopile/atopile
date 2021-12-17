# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest

# Netlists --------------------------------------------------------------------
def test_netlist_graph():
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist import make_t2_netlist_from_t1
    from faebryk.library import VirtualComponent, SMD_Resistor

    gnd = VirtualComponent(
        name="GND",
        pins=[1],
    )

    vcc = VirtualComponent(
        name="+3V3",
        pins=[1],
    )

    resistor1 = SMD_Resistor(
        name="1",
        value="R",
        footprint_subtype="R_0805_2012Metric",
    )

    resistor2 = SMD_Resistor(
        name="2",
        value="R",
        footprint_subtype="R_0805_2012Metric",
    )

    resistor1.connect(1, vcc)
    resistor1.connect(2, gnd)
    resistor2.connect_zip(resistor1)

    comps = [gnd, vcc, resistor1, resistor2]
    netlist = from_faebryk_t2_netlist(
        make_t2_netlist_from_t1(
            [comp.get_comp() for comp in comps]
        )
    )

    _,netlist_t1 = test_netlist_t1()
    success = netlist == netlist_t1
    if not success:
        print("Graph != T1")
        print("T1", netlist_t1)
        print("Graph", netlist)

    return success, netlist

def test_netlist_t1():
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist import make_t2_netlist_from_t1

    gnd = {
        "vertex": {
            "name": "GND",
            "real": False,
            "neighbors": {1: []},
        },
        "pin": 1,
    }

    vcc = {
        "vertex": {
            "name": "+3V3",
            "real": False,
            "neighbors": {1: []},
        },
        "pin": 1,
    }

    resistor1 = {
        "name": "R1",
        "value": "R",
        "properties": {
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
        "real": True,
        "neighbors": {1: [], 2: []},
    }

    resistor2 = {
        "name": "R2",
        "value": "R",
        "properties": {
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
        "real": True,
        "neighbors": {1: [], 2: []},
    }

    resistor1["neighbors"][1].append(vcc)
    resistor1["neighbors"][2].append(gnd)

    resistor2["neighbors"][1].append(vcc)
    resistor2["neighbors"][2].append(gnd)


    t1_netlist = [resistor1, resistor2, gnd["vertex"], vcc["vertex"]]

    t2_netlist = make_t2_netlist_from_t1(t1_netlist)
    kicad_netlist = from_faebryk_t2_netlist(t2_netlist)

    _, netlist_t2 = test_netlist_t2()
    kicad_netlist_t2 = from_faebryk_t2_netlist(netlist_t2)

    success = kicad_netlist == kicad_netlist_t2
    if not success:
        print("T1 != T2")
        print("T2", kicad_netlist_t2)
        print("T1", kicad_netlist)

    return success, kicad_netlist

def test_netlist_t2():
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist

    # t2_netlist = [(properties, vertices=[comp=(name, value, properties), pin)])]

    resistor1 = {
        "name": "R1",
        "value": "R",
        "properties": {
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    }

    resistor2 = {
        "name": "R2",
        "value": "R",
        "properties": {
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    }

    netlist = [
        {
            "properties": {
                "name": "GND",
            },
            "vertices": [
                {
                    "comp": resistor1,
                    "pin": 2
                },
                {
                    "comp": resistor2,
                    "pin": 2
                },
            ],
        },
        {
            "properties": {
                "name": "+3V3",
            },
            "vertices": [
                {
                    "comp": resistor1,
                    "pin": 1
                },
                {
                    "comp": resistor2,
                    "pin": 1
                },
            ],
        },
    ]
    #print("T2 netlist:", netlist)

    kicad_net = from_faebryk_t2_netlist(netlist)
    kicad_net_manu = _test_netlist_manu()

    success = kicad_net == kicad_net_manu
    if not success:
        print("T2 != Manu")
        print(kicad_net_manu)

    return success, netlist

def _test_netlist_manu():
    import itertools
    from faebryk.exporters.netlist.kicad.netlist_kicad import _defaulted_comp, _gen_net, _gen_node, _defaulted_netlist
    import faebryk.exporters.netlist.kicad.sexp as sexp
    # Footprint pins are just referenced by number through netlist of symbol

    # We only need
    #   - components
    #       - ref
    #       - value (for silk)
    #       - footprint
    #       - tstamp (uuid gen)
    #   - nets
    #       - code (uuid gen)
    #       - name
    #       - nodes
    #           - ref (comp)
    #           - pin (of footprint)

    # Careful comps need distinct timestamps
    tstamp = itertools.count(1)

    resistor_comp = _defaulted_comp(
        ref="R1",
        value="R",
        footprint="Resistor_SMD:R_0805_2012Metric",
        tstamp=next(tstamp),
    )
    resistor_comp2 = _defaulted_comp(
        ref="R2",
        value="R",
        footprint="Resistor_SMD:R_0805_2012Metric",
        tstamp=next(tstamp),
    )

    device_nets = [
        _gen_net(
            code=1,
            name="+3V3",
            nodes=[
                _gen_node(
                    ref="R1",
                    pin=1,
                ),
                _gen_node(
                    ref="R2",
                    pin=1,
                ),
            ],
        ),
        _gen_net(
            code=2,
            name="GND",
            nodes=[
                _gen_node(
                    ref="R1",
                    pin=2,
                ),
                _gen_node(
                    ref="R2",
                    pin=2,
                ),
            ],
        ),
    ]

    netlist = _defaulted_netlist(
        components=[resistor_comp, resistor_comp2],
        nets=[*device_nets],
    )

    sexpnet = sexp.gensexp(netlist)

    return sexpnet

class TestNetlist(unittest.TestCase):
    def test_netlist(self):
        ok, _ = test_netlist_t2()
        self.assertTrue(ok)

        ok, _ = test_netlist_t1()
        self.assertTrue(ok)

        ok, _ = test_netlist_graph()
        self.assertTrue(ok)