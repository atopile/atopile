# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
Faebryk samples demonstrate the usage by building example systems.
This particular sample creates a netlist with some resistors and a nand ic
    with no specific further purpose or function.
It shall primarily demonstrate some simple faebryk concepts.
Thus this is a netlist sample.
Netlist samples can be run directly.
"""

import logging

import faebryk.library._F as F
import typer
from faebryk.core.core import Module
from faebryk.core.util import connect_interfaces_via_chain
from faebryk.exporters.netlist.graph import attach_nets_and_kicad_info
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.exporters.netlist.netlist import make_t2_netlist_from_graph
from faebryk.library._F import Constant
from faebryk.libs.experiments.buildutil import export_graph, export_netlist
from faebryk.libs.logging import setup_basic_logging

logger = logging.getLogger(__name__)


def App():
    # power
    class Battery(Module):
        class _IFS(Module.IFS()):
            power = F.ElectricPower()

        def __init__(self) -> None:
            super().__init__()
            self.IFs = Battery._IFS(self)

            self.add_trait(
                F.can_attach_to_footprint_via_pinmap(
                    {"1": self.IFs.power.IFs.hv, "2": self.IFs.power.IFs.lv}
                )
            ).attach(
                F.KicadFootprint.with_simple_names(
                    "Battery:BatteryHolder_ComfortableElectronic_CH273-2450_1x2450", 2
                )
            )
            self.add_trait(F.has_simple_value_representation_defined("B"))

    battery = Battery()

    # functional components
    resistor1 = F.Resistor().builder(lambda r: r.PARAMs.resistance.merge(Constant(100)))
    resistor2 = F.Resistor().builder(lambda r: r.PARAMs.resistance.merge(Constant(100)))
    cd4011 = F.TI_CD4011BE()

    # aliases
    power = F.ElectricPower()
    vcc = F.Electrical()
    gnd = F.Electrical()
    high = F.ElectricLogic()
    low = F.ElectricLogic()

    power.connect(battery.IFs.power)
    power.IFs.hv.connect(vcc)
    power.IFs.lv.connect(gnd)

    high.connect_to_electric(vcc, power)
    low.connect_to_electric(gnd, power)

    # connections
    connect_interfaces_via_chain(vcc, [resistor1, resistor2], gnd)

    cd4011.NODEs.gates[0].IFs.inputs[0].connect(high)
    cd4011.NODEs.gates[0].IFs.inputs[1].connect(low)
    cd4011.IFs.power.connect(battery.IFs.power)

    # make netlist exportable (packages, pinmaps)
    for r in [
        resistor1,
        resistor2,
    ]:
        r.get_trait(F.can_attach_to_footprint).attach(
            F.SMDTwoPin(F.SMDTwoPin.Type._0805)
        )

    # Export
    app = Module()
    app.NODEs.components = [
        battery,
        resistor1,
        resistor2,
        cd4011,
    ]

    return app


def main(make_graph: bool = True, show_graph: bool = True):
    logger.info("Building app")
    app = App()

    # make graph
    logger.info("Make graph")
    G = app.get_graph()

    logger.info("Make netlist")
    attach_nets_and_kicad_info(G)
    t2 = make_t2_netlist_from_graph(G)
    netlist = from_faebryk_t2_netlist(t2)

    export_netlist(netlist)

    if make_graph:
        logger.info("Make render")
        export_graph(G.G, show=True)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running experiment")

    typer.run(main)
