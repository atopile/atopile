# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
Faebryk samples demonstrate the usage by building example systems.
This particular sample creates a netlist with some resistors and a nand ic 
    with no specific further purpose or function.
Thus this is a netlist sample.
Netlist samples can be run directly.
The netlist is printed to stdout.
"""
from pathlib import Path
import logging

logger = logging.getLogger("main")


def run_experiment():
    # function imports
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist import make_t2_netlist_from_t1
    from faebryk.exporters.netlist.graph import (
        make_graph_from_components,
        make_t1_netlist_from_graph,
    )

    # library imports
    from faebryk.library.core import Component
    from faebryk.library.library.components import Resistor, TI_CD4011BE
    from faebryk.library.library.footprints import SMDTwoPin
    from faebryk.library.library.interfaces import Power
    from faebryk.library.library.parameters import Constant
    from faebryk.library.trait_impl.component import (
        has_defined_footprint,
        has_symmetric_footprint_pinmap,
    )

    # power
    battery = Component()
    battery.IFs.power = Power()

    # functional components
    resistor1 = Resistor(Constant(100))
    resistor2 = Resistor(Constant(100))
    cd4011 = TI_CD4011BE()

    # aliases
    vcc = battery.IFs.power.IFs.hv
    gnd = battery.IFs.power.IFs.lv

    # connections
    resistor1.IFs.next().connect(vcc).connect(resistor2.IFs.next())
    resistor1.IFs.next().connect(gnd).connect(resistor2.IFs.next())
    cd4011.CMPs.nands[0].IFs.inputs[0].connect(vcc)
    cd4011.CMPs.nands[0].IFs.inputs[1].connect(gnd)
    cd4011.IFs.power.connect(battery.IFs.power)

    # make kicad netlist exportable (packages, pinmaps)
    for r in [resistor1, resistor2]:
        r.add_trait(has_defined_footprint(SMDTwoPin(SMDTwoPin.Type._0805)))
        r.add_trait(has_symmetric_footprint_pinmap())
    battery.add_trait(has_symmetric_footprint_pinmap())

    comps = [
        resistor1,
        resistor2,
        cd4011,
        battery,
    ]

    t1_ = make_t1_netlist_from_graph(make_graph_from_components(comps))

    netlist = from_faebryk_t2_netlist(make_t2_netlist_from_t1(t1_))


    path = Path("./build/faebryk.net")
    logger.info("Writing Experiment netlist to {}".format(path.absolute()))
    path.write_text(netlist)

    from faebryk.exporters.netlist import render_graph

    render_graph(t1_)


# Boilerplate -----------------------------------------------------------------
import sys


def main(argc, argv, argi):
    logging.basicConfig(level=logging.INFO)

    logger.info("Running experiment")
    run_experiment()


if __name__ == "__main__":
    import os
    import sys

    root = os.path.join(os.path.dirname(__file__), "..")
    sys.path.append(root)
    main(len(sys.argv), sys.argv, iter(sys.argv))
