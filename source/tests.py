from sexp.test.sexptest import test_sexp

def run_tests():
    success = test_sexp()
    if not success:
        print("Sexp tests: failed")
        return success

    success, netlist = test_netlist_t2()
    if not success:
        print("T2 netlist test: failed")
        return success

    success, netlist = test_netlist_t1()
    if not success:
        print("T1 netlist test: failed")
        return success

    success, netlist = test_netlist_graph()
    if not success:
        print("Graph netlist test: failed")
        return success

    return success

# TESTS =======================================================================
# Sexp ------------------------------------------------------------------------
def test_sexp():
    from sexp.test.sexptest import test_sexp
    return test_sexp()

# Netlists --------------------------------------------------------------------
def test_netlist_graph():
    from netlist.kicad_netlist import from_faebryk_t2_netlist
    from netlist.netlist import make_t2_netlist_from_t1
    from experiment import make_t1_netlist_from_graph
    from library import VirtualComponent, SMD_Resistor

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
            make_t1_netlist_from_graph(comps)
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
    from netlist.kicad_netlist import from_faebryk_t2_netlist
    from netlist.netlist import make_t2_netlist_from_t1

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
    from netlist.kicad_netlist import from_faebryk_t2_netlist

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
    from netlist.kicad_netlist import _defaulted_comp, _gen_net, _gen_node, _defaulted_netlist
    from sexp import sexp
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