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
import logging

from faebryk.exporters.netlist import make_t2_netlist_from_t1
from faebryk.exporters.netlist.graph import (
    make_graph_from_components,
    make_t1_netlist_from_graph,
)
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.library.core import Component, Footprint, Parameter
from faebryk.library.kicad import has_kicad_manual_footprint
from faebryk.library.library.components import LED, MOSFET, Resistor, Switch
from faebryk.library.library.footprints import SMDTwoPin
from faebryk.library.library.interfaces import Electrical, Power
from faebryk.library.library.parameters import TBD, Constant
from faebryk.library.trait_impl.component import (
    has_defined_footprint,
    has_defined_footprint_pinmap,
    has_symmetric_footprint_pinmap,
)
from faebryk.library.traits.component import has_footprint_pinmap
from faebryk.library.util import get_all_components
from faebryk.libs.experiments.buildutil import export_graph, export_netlist

logger = logging.getLogger("main")


def run_experiment():
    # power
    class Battery(Component):
        def __init__(self) -> None:
            super().__init__()

            class _IFs(Component.InterfacesCls()):
                power = Power()

            self.IFs = _IFs(self)
            self.voltage: Parameter = TBD()

    class LED_Indicator(Component):
        def __init__(self) -> None:
            super().__init__()

            class _ifs(Component.InterfacesCls()):
                input_power = Power()
                input_control = Electrical()

            class _cmps(Component.ComponentsCls()):
                led = LED()
                current_limiting_resistor = Resistor(TBD())
                switch = MOSFET()

            self.IFs = _ifs(self)
            self.CMPs = _cmps(self)

            # fabric
            # TODO
            self.CMPs.led.IFs.cathode.connect_via(
                self.CMPs.current_limiting_resistor, self.IFs.input_power.IFs.lv
            )
            self.CMPs.led.IFs.anode.connect(self.CMPs.switch.IFs.drain)

            self.CMPs.switch.IFs.source.connect(self.IFs.input_power.IFs.hv)
            self.CMPs.switch.IFs.gate.connect(self.IFs.input_control)

    class LogicSwitch(Component):
        def __init__(self) -> None:
            super().__init__()

            class _ifs(Component.InterfacesCls()):
                input_power = Power()
                output_control = Electrical()

            class _cmps(Component.ComponentsCls()):
                switch = Switch()
                pull_down_resistor = Resistor(TBD())

            self.IFs = _ifs(self)
            self.CMPs = _cmps(self)

            # fabric
            self.IFs.input_power.IFs.hv.connect_via(
                self.CMPs.switch, self.IFs.output_control
            )
            self.IFs.input_power.IFs.lv.connect_via(
                self.CMPs.pull_down_resistor, self.IFs.output_control
            )

    class App(Component):
        def __init__(self) -> None:
            super().__init__()

            class _ifs(Component.InterfacesCls()):
                pass

            class _cmps(Component.ComponentsCls()):
                battery = Battery()
                led_ind = LED_Indicator()
                switch = LogicSwitch()

            self.IFs = _ifs(self)
            self.CMPs = _cmps(self)

            # fabric
            power = self.CMPs.battery.IFs.power

            power.connect(self.CMPs.led_ind.IFs.input_power)
            power.connect(self.CMPs.switch.IFs.input_power)
            self.CMPs.switch.IFs.output_control.connect(
                self.CMPs.led_ind.IFs.input_control
            )

    app = App()

    # parametrizing
    app.CMPs.battery.voltage = Constant(5)
    app.CMPs.switch.CMPs.pull_down_resistor.set_resistance(Constant(100_000))
    app.CMPs.led_ind.CMPs.led.set_forward_parameters(
        voltage_V=Constant(2.4), current_A=Constant(0.020)
    )
    app.CMPs.led_ind.CMPs.current_limiting_resistor.set_resistance(
        app.CMPs.led_ind.CMPs.led.get_trait(
            LED.has_calculatable_needed_series_resistance
        ).get_needed_series_resistance_ohm(app.CMPs.battery.voltage.value)
    )

    # packaging
    for smd_comp in [
        app.CMPs.led_ind.CMPs.led,
        app.CMPs.led_ind.CMPs.current_limiting_resistor,
        app.CMPs.switch.CMPs.pull_down_resistor,
    ]:
        smd_comp.add_trait(has_defined_footprint(SMDTwoPin(SMDTwoPin.Type._0805)))

    switch_fp = Footprint()
    switch_fp.add_trait(has_kicad_manual_footprint("Panasonic_EVQPUJ_EVQPUA"))
    app.CMPs.switch.CMPs.switch.add_trait(has_defined_footprint(switch_fp))

    for symmetric_component in [
        app.CMPs.switch.CMPs.pull_down_resistor,
        app.CMPs.switch.CMPs.switch,
        app.CMPs.led_ind.CMPs.current_limiting_resistor,
    ]:
        symmetric_component.add_trait(has_symmetric_footprint_pinmap())

    app.CMPs.led_ind.CMPs.led.add_trait(
        has_defined_footprint_pinmap(
            {
                1: app.CMPs.led_ind.CMPs.led.IFs.anode,
                2: app.CMPs.led_ind.CMPs.led.IFs.cathode,
            }
        )
    )

    # TODO: remove, just compensation for old graph
    for i in get_all_components(app) + [app]:
        if i.has_trait(has_footprint_pinmap):
            continue
        i.add_trait(has_symmetric_footprint_pinmap())

    # make graph
    components = [app]

    t1_ = make_t1_netlist_from_graph(make_graph_from_components(components))

    netlist = from_faebryk_t2_netlist(make_t2_netlist_from_t1(t1_))
    assert netlist is not None

    export_netlist(netlist)
    export_graph(t1_, show=True)


# Boilerplate -----------------------------------------------------------------
def main(argc, argv, argi):
    logging.basicConfig(level=logging.INFO)

    logger.info("Running experiment")
    run_experiment()


if __name__ == "__main__":
    import sys

    main(len(sys.argv), sys.argv, iter(sys.argv))
