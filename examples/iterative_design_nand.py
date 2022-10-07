# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
Faebryk samples demonstrate the usage by building example systems.
This particular sample creates a netlist with an led and a nand ic 
    that creates some logic. 
The goal of this sample is to show how faebryk can be used to iteratively
    expand the specifics of a design in multiple steps.
Thus this is a netlist sample.
Netlist samples can be run directly.
The netlist is printed to stdout.
"""
from pathlib import Path
import logging

logger = logging.getLogger("main")


def run_experiment():
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist import make_t2_netlist_from_t1
    from faebryk.exporters.netlist.graph import (
        make_graph_from_components,
        make_t1_netlist_from_graph,
    )
    from faebryk.library.core import Component, Footprint
    from faebryk.library.library.components import CD4011, LED, NAND, Resistor, Switch
    from faebryk.library.library.footprints import DIP, SMDTwoPin
    from faebryk.library.library.interfaces import Electrical, Power
    from faebryk.library.library.parameters import TBD, Constant
    from faebryk.library.trait_impl.component import (
        has_defined_footprint,
        has_defined_footprint_pinmap,
        has_symmetric_footprint_pinmap,
    )
    from faebryk.library.kicad import has_kicad_manual_footprint

    # levels
    high = Electrical()
    low = Electrical()

    # power
    battery = Component()
    battery.IFs.power = Power()

    # alias
    gnd = battery.IFs.power.IFs.lv
    power = battery.IFs.power

    # logic
    nands = [NAND(2) for _ in range(2)]
    nands[0].IFs.inputs[1].connect(low)
    nands[1].IFs.inputs[0].connect(nands[0].IFs.output)
    nands[1].IFs.inputs[1].connect(low)
    logic_in = nands[0].IFs.inputs[0]
    logic_out = nands[1].IFs.output

    # led
    current_limiting_resistor = Resistor(resistance=TBD())
    led = LED()
    led.IFs.cathode.connect_via(current_limiting_resistor, gnd)

    # application
    switch = Switch()
    pull_down_resistor = Resistor(TBD())

    logic_in.connect_via(pull_down_resistor, low)
    logic_in.connect_via(switch, high)
    logic_out.connect(led.IFs.anode)

    # parametrizing
    battery.voltage = 5
    pull_down_resistor.set_resistance(Constant(100_000))
    led.set_forward_parameters(voltage_V=Constant(2.4), current_A=Constant(0.020))
    nand_ic = CD4011().get_trait(CD4011.constructable_from_nands).from_nands(nands)
    nand_ic.IFs.power.connect(power)
    high.connect(power.IFs.hv)
    low.connect(power.IFs.lv)
    current_limiting_resistor.set_resistance(
        led.get_trait(
            LED.has_calculatable_needed_series_resistance
        ).get_needed_series_resistance_ohm(battery.voltage)
    )

    # packaging
    nand_ic.add_trait(
        has_defined_footprint(DIP(pin_cnt=14, spacing_mm=7.62, long_pads=False))
    )
    nand_ic.add_trait(
        has_defined_footprint_pinmap(
            {
                7: nand_ic.IFs.power.IFs.lv,
                14: nand_ic.IFs.power.IFs.hv,
                3: nand_ic.connection_map[nand_ic.CMPs.nands[0].IFs.output],
                4: nand_ic.connection_map[nand_ic.CMPs.nands[1].IFs.output],
                11: nand_ic.connection_map[nand_ic.CMPs.nands[2].IFs.output],
                10: nand_ic.connection_map[nand_ic.CMPs.nands[3].IFs.output],
                1: nand_ic.connection_map[nand_ic.CMPs.nands[0].IFs.inputs[0]],
                2: nand_ic.connection_map[nand_ic.CMPs.nands[0].IFs.inputs[1]],
                5: nand_ic.connection_map[nand_ic.CMPs.nands[1].IFs.inputs[0]],
                6: nand_ic.connection_map[nand_ic.CMPs.nands[1].IFs.inputs[1]],
                12: nand_ic.connection_map[nand_ic.CMPs.nands[2].IFs.inputs[0]],
                13: nand_ic.connection_map[nand_ic.CMPs.nands[2].IFs.inputs[1]],
                9: nand_ic.connection_map[nand_ic.CMPs.nands[3].IFs.inputs[0]],
                8: nand_ic.connection_map[nand_ic.CMPs.nands[3].IFs.inputs[1]],
            }
        )
    )

    for smd_comp in [led, pull_down_resistor, current_limiting_resistor]:
        smd_comp.add_trait(has_defined_footprint(SMDTwoPin(SMDTwoPin.Type._0805)))

    switch_fp = Footprint()
    switch_fp.add_trait(has_kicad_manual_footprint("Panasonic_EVQPUJ_EVQPUA"))
    switch.add_trait(has_defined_footprint(switch_fp))

    for symmetric_component in [pull_down_resistor, current_limiting_resistor, switch]:
        symmetric_component.add_trait(has_symmetric_footprint_pinmap())

    led.add_trait(
        has_defined_footprint_pinmap(
            {
                1: led.IFs.anode,
                2: led.IFs.cathode,
            }
        )
    )

    # TODO: remove, just compensation for old graph
    battery.add_trait(has_symmetric_footprint_pinmap())
    logic_virt = Component()
    logic_virt.IFs.high = high
    logic_virt.IFs.low = low
    logic_virt.add_trait(has_symmetric_footprint_pinmap())
    for n in nand_ic.CMPs.nands:
        n.add_trait(has_symmetric_footprint_pinmap())

    # make graph
    components = [
        led,
        pull_down_resistor,
        current_limiting_resistor,
        nand_ic,
        switch,
        battery,
        logic_virt,
    ]

    t1_ = make_t1_netlist_from_graph(make_graph_from_components(components))

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
