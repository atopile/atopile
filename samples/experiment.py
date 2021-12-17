# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

# Test stuff ------------------------------------------------------------------
def make_t1_netlist_from_graph(comps):
    t1_netlist = [comp.get_comp() for comp in comps]

    return t1_netlist


def run_experiment():
    import faebryk.library as lib
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist import make_t2_netlist_from_t1

    gnd = lib.VirtualComponent(
        name="GND",
        pins=[1],
    )

    vcc = lib.VirtualComponent(
        name="+3V3",
        pins=[1],
    )

    resistor1 = lib.SMD_Resistor(
        name="1",
        value="R",
        footprint_subtype="R_0805_2012Metric",
    )

    resistor2 = lib.SMD_Resistor(
        name="2",
        value="R",
        footprint_subtype="R_0805_2012Metric",
    )

    cd4011 = lib.CD4011("nandboi", "digikey-footprints:DIP-14_W3mm")
    cd4011.connect_power(vcc, gnd)
    cd4011.nands[0].connect_in1(vcc)
    cd4011.nands[0].connect_in2(gnd)

    resistor1.connect(1, vcc)
    resistor1.connect(2, gnd)
    resistor2.connect_zip(resistor1)

    comps = [gnd, vcc,
        resistor1, resistor2,
        cd4011, *cd4011.nands
    ]
    netlist = from_faebryk_t2_netlist(
        make_t2_netlist_from_t1(
            make_t1_netlist_from_graph(comps)
        )
    )

    print("Experiment netlist:")
    print(netlist)

    #from faebryk.exporters.netlist import render_graph
    #render_graph(make_t1_netlist_from_graph(comps))

import sys
import logging

def main(argc, argv, argi):
    logging.basicConfig(level=logging.INFO)

    print("Running experiment")
    run_experiment()

if __name__ == "__main__":
    import os
    import sys
    root = os.path.join(os.path.dirname(__file__), '..')
    sys.path.append(root)
    main(len(sys.argv), sys.argv, iter(sys.argv))
