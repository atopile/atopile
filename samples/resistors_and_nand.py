# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


def run_experiment():
    # function imports
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist import make_t2_netlist_from_t1
    from faebryk.exporters.netlist.graph import make_graph_from_components, make_t1_netlist_from_graph
    # library imports
    from faebryk.library.core import Component
    from faebryk.library.library.components import Resistor, TI_CD4011BE
    from faebryk.library.library.footprints import SMDTwoPin
    from faebryk.library.library.interfaces import Power
    from faebryk.library.library.parameters import Constant
    from faebryk.library.traits.component import has_defined_footprint, has_symmetric_footprint_pinmap, has_defined_interfaces

    # power
    battery = Component()
    battery.power = Power()
    battery.add_trait(has_defined_interfaces([battery.power]))
    battery.power.set_component(battery)

    # functional components
    resistor1 = Resistor(Constant(100))
    resistor2 = Resistor(Constant(100))
    cd4011 = TI_CD4011BE()

    # aliases
    vcc = battery.power.hv
    gnd = battery.power.lv

    # connections
    resistor1.interfaces[0].connect(vcc)
    resistor1.interfaces[1].connect(gnd)
    resistor2.interfaces[0].connect(resistor1.interfaces[0])
    resistor2.interfaces[1].connect(resistor1.interfaces[1])
    cd4011.nands[0].inputs[0].connect(vcc)
    cd4011.nands[0].inputs[1].connect(gnd)
    cd4011.power.connect(battery.power)

    # make kicad netlist exportable (packages, pinmaps)
    for r in [resistor1, resistor2]:
        r.add_trait(has_defined_footprint(SMDTwoPin(
            SMDTwoPin.Type._0805
        )))
        r.add_trait(has_symmetric_footprint_pinmap(r))
    battery.add_trait(has_symmetric_footprint_pinmap(battery))


    comps = [
        resistor1,
        resistor2,
        cd4011,
        *cd4011.nands,
        battery,
    ]

    t1_ = make_t1_netlist_from_graph(
            make_graph_from_components(comps)
        )

    netlist = from_faebryk_t2_netlist(
        make_t2_netlist_from_t1(
            t1_
        )
    )

    print("Experiment netlist:")
    print(netlist)

    from faebryk.exporters.netlist import render_graph
    render_graph(t1_)

# Boilerplate -----------------------------------------------------------------
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
 