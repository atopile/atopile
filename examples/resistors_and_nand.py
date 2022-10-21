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
import logging

# function imports
from faebryk.exporters.netlist import make_t2_netlist_from_t1
from faebryk.exporters.netlist.graph import (
    make_graph_from_components,
    make_t1_netlist_from_graph,
)
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist

# library imports
from faebryk.library.core import Component
from faebryk.library.library.components import TI_CD4011BE, Resistor
from faebryk.library.library.footprints import SMDTwoPin
from faebryk.library.library.interfaces import Power
from faebryk.library.library.parameters import Constant
from faebryk.library.trait_impl.component import (
    has_defined_footprint,
    has_symmetric_footprint_pinmap,
)
from faebryk.libs.experiments.buildutil import export_graph, export_netlist

logger = logging.getLogger("main")


def run_experiment():

    # power
    class Battery(Component):
        class _IFS(Component.InterfacesCls()):
            power = Power()

        def __init__(self) -> None:
            super().__init__()
            self.IFs = Battery._IFS(self)

    battery = Battery()

    # functional components
    resistor1 = Resistor(Constant(100))
    resistor2 = Resistor(Constant(100))
    cd4011 = TI_CD4011BE()

    # aliases
    vcc = battery.IFs.power.IFs.hv
    gnd = battery.IFs.power.IFs.lv

    # connections
    r1it = iter(resistor1.IFs.get_all())
    r2it = iter(resistor2.IFs.get_all())
    next(r1it).connect(vcc).connect(next(r2it))
    next(r1it).connect(gnd).connect(next(r2it))
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
    assert netlist is not None

    export_netlist(netlist)
    export_graph(t1_, show=True)


# Boilerplate -----------------------------------------------------------------
import sys


def main(argc, argv, argi):
    logging.basicConfig(level=logging.INFO)

    logger.info("Running experiment")
    run_experiment()


if __name__ == "__main__":
    import sys

    main(len(sys.argv), sys.argv, iter(sys.argv))
