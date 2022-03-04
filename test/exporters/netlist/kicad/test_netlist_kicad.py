# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest

# Netlists --------------------------------------------------------------------
def test_netlist_graph():
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist import make_t2_netlist_from_t1
    from faebryk.library.core import Component
    from faebryk.library.library.interfaces import Electrical
    from faebryk.library.traits.component import has_defined_footprint
    from faebryk.library.core import Footprint
    from faebryk.library.kicad import has_defined_kicad_ref
    from faebryk.library.traits.component import has_defined_footprint_pinmap, has_defined_type_description, has_interfaces, has_interfaces_list, has_type_description
    from faebryk.library.kicad import has_kicad_manual_footprint
    from faebryk.exporters.netlist.graph import make_t1_netlist_from_graph, make_graph_from_components

    
    # component definition
    gnd = Electrical()
    vcc = Electrical()
    resistor1 = Component()
    resistor2 = Component()

    # name
    resistor1.add_trait(has_defined_kicad_ref("R1"))
    resistor2.add_trait(has_defined_kicad_ref("R2"))

    for r in [resistor1, resistor2]:
        # value
        r.add_trait(has_defined_type_description("R"))
        # interfaces
        r.interfaces = [Electrical(), Electrical()]
        r.add_trait(has_interfaces_list(r))
        r.get_trait(has_interfaces).set_interface_comp(r)
        # footprint
        fp = Footprint()
        fp.add_trait(has_kicad_manual_footprint("Resistor_SMD:R_0805_2012Metric"))
        r.add_trait(has_defined_footprint(fp))
        # pinmap
        r.add_trait(has_defined_footprint_pinmap(
            {
                1: r.interfaces[0],
                2: r.interfaces[1],
            }
        ))

    resistor1.interfaces[0].connect(vcc)
    resistor1.interfaces[1].connect(gnd)
    resistor2.interfaces[0].connect(resistor1.interfaces[0])
    resistor2.interfaces[1].connect(resistor1.interfaces[1])

    # net naming
    net_wrappers = []
    for i in [gnd, vcc]:
        wrap = Component()
        wrap.interfaces = [i]
        wrap.add_trait(has_interfaces_list(wrap))
        wrap.get_trait(has_interfaces).set_interface_comp(wrap)
        wrap.add_trait(has_defined_kicad_ref("+3V3" if i == vcc else "GND"))
        wrap.add_trait(has_defined_footprint_pinmap({1: i}))
        net_wrappers.append(wrap)

    # Make netlist
    comps = [
        resistor1,
        resistor2,
        *net_wrappers,
    ]
    netlist = from_faebryk_t2_netlist(
        make_t2_netlist_from_t1(
            make_t1_netlist_from_graph(
                make_graph_from_components(
                    comps
                )
            )
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
    from faebryk.exporters.netlist import Net, Vertex, Component

    # t2_netlist = [(properties, vertices=[comp=(name, value, properties), pin)])]

    resistor1 = Component(
        name = "R1",
        value = "R",
        properties = {
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    )

    resistor2 = Component(
        name = "R2",
        value = "R",
        properties = {
            "footprint": "Resistor_SMD:R_0805_2012Metric",
        },
    )

    netlist = [
        Net(
            properties = {
                "name": "GND",
            },
            vertices = [
                Vertex(
                    component = resistor1,
                    pin = 2,
                ),
                Vertex(
                    component = resistor2,
                    pin = 2,
                ),
            ],
        ),
        Net(
            properties = {
                "name": "+3V3",
            },
            vertices = [
                Vertex(
                    component = resistor1,
                    pin = 1,
                ),
                Vertex(
                    component = resistor2,
                    pin = 1,
                ),
            ],
        ),
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
