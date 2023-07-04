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
"""
import logging

import typer
from faebryk.core.core import Module, Parameter
from faebryk.core.util import get_all_nodes, specialize_interface, specialize_module
from faebryk.exporters.netlist.graph import make_t1_netlist_from_graph
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.exporters.netlist.netlist import make_t2_netlist_from_t1
from faebryk.exporters.visualize.graph import render_matrix
from faebryk.library.can_attach_to_footprint import can_attach_to_footprint
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_defined_type_description import has_defined_type_description
from faebryk.library.KicadFootprint import KicadFootprint
from faebryk.library.LED import LED
from faebryk.library.Logic import Logic
from faebryk.library.NAND import NAND
from faebryk.library.Resistor import Resistor
from faebryk.library.SMDTwoPin import SMDTwoPin
from faebryk.library.Switch import Switch
from faebryk.library.TBD import TBD
from faebryk.library.TI_CD4011BE import TI_CD4011BE
from faebryk.libs.experiments.buildutil import export_netlist
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class Battery(Module):
    def __init__(self) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            power = ElectricPower()

        self.IFs = IFS(self)
        self.voltage: Parameter = TBD()


class PowerSource(Module):
    def __init__(self) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            power_out = ElectricPower()

        self.IFs = IFS(self)


class XOR(Module):
    def __init__(
        self,
    ):
        super().__init__()

        class IFS(Module.IFS()):
            inputs = times(2, Logic)
            output = Logic()

        self.IFs = IFS(self)

    def xor(self, in1: Logic, in2: Logic):
        self.IFs.inputs[0].connect(in1)
        self.IFs.inputs[1].connect(in2)
        return self.IFs.output


class XOR_with_NANDS(XOR):
    def __init__(
        self,
    ):
        super().__init__()

        class NODES(Module.NODES()):
            nands = times(4, lambda: NAND(2))

        self.NODEs = NODES(self)

        A = self.IFs.inputs[0]
        B = self.IFs.inputs[1]

        G = self.NODEs.nands
        Q = self.IFs.output

        # ~(a&b)
        q0 = G[0].nand(A, B)
        # ~(a&~b)
        q1 = G[1].nand(A, q0)
        # ~(~a&b)
        q2 = G[2].nand(B, q0)
        # (a&~b) o| (~a&b)
        q3 = G[3].nand(q1, q2)

        Q.connect(q3)


def main(make_graph: bool = True):
    # levels
    on = Logic()
    off = Logic()

    # power
    power_source = PowerSource()

    # alias
    power = power_source.IFs.power_out
    gnd = Electrical().connect(power.NODEs.lv)

    # logic
    logic_in = Logic()
    logic_out = Logic()

    xor = XOR()
    logic_out.connect(xor.xor(logic_in, on))

    # led
    current_limiting_resistor = Resistor(resistance=TBD())
    led = LED()
    led.IFs.cathode.connect_via(current_limiting_resistor, gnd)

    # application
    switch = Switch(Logic)()

    logic_in.connect_via(switch, on)

    e_in = specialize_interface(logic_in, ElectricLogic())
    pull_down_resistor = Resistor(TBD())
    e_in.pull_down(pull_down_resistor)

    e_out = specialize_interface(logic_out, ElectricLogic())
    e_out.NODEs.signal.connect(led.IFs.anode)

    specialize_interface(on, ElectricLogic()).connect_to_electric(power.NODEs.hv, power)
    specialize_interface(off, ElectricLogic()).connect_to_electric(
        power.NODEs.lv, power
    )

    nxor = specialize_module(xor, XOR_with_NANDS())

    battery = specialize_module(power_source, Battery())

    el_switch = specialize_module(switch, Switch(ElectricLogic)())
    e_switch = Switch(Electrical)()
    # TODO make switch generic to remove the asserts
    for e, el in zip(e_switch.IFs.unnamed, el_switch.IFs.unnamed):
        assert isinstance(el, ElectricLogic)
        assert isinstance(e, Electrical)
        el.connect_to_electric(e, battery.IFs.power)

    # build graph
    app = Module()
    app.NODEs.components = [
        led,
        pull_down_resistor,
        current_limiting_resistor,
        switch,
        battery,
        e_switch,
    ]

    # parametrizing
    pull_down_resistor.set_resistance(Constant(100_000))

    for node in get_all_nodes(app):
        if isinstance(node, Battery):
            node.voltage = Constant(5)

        if isinstance(node, LED):
            node.set_forward_parameters(
                voltage_V=Constant(2.4), current_A=Constant(0.020)
            )

    assert isinstance(battery.voltage, Constant)
    current_limiting_resistor.set_resistance(
        led.get_trait(
            LED.has_calculatable_needed_series_resistance
        ).get_needed_series_resistance_ohm(battery.voltage.value)
    )

    # packaging
    e_switch.get_trait(can_attach_to_footprint).attach(
        KicadFootprint.with_simple_names("Panasonic_EVQPUJ_EVQPUA", 2)
    )
    for node in get_all_nodes(app):
        if isinstance(node, Battery):
            node.add_trait(
                can_attach_to_footprint_via_pinmap(
                    {"1": node.IFs.power.NODEs.hv, "2": node.IFs.power.NODEs.lv}
                )
            ).attach(
                KicadFootprint.with_simple_names(
                    "BatteryHolder_ComfortableElectronic_CH273-2450_1x2450", 2
                )
            )
            node.add_trait(has_defined_type_description("B"))

        if isinstance(node, Resistor):
            node.get_trait(can_attach_to_footprint).attach(
                SMDTwoPin(SMDTwoPin.Type._0805)
            )

        if isinstance(node, LED):
            node.add_trait(
                can_attach_to_footprint_via_pinmap(
                    {"1": node.IFs.anode, "2": node.IFs.cathode}
                )
            ).attach(SMDTwoPin(SMDTwoPin.Type._0805))

    # packages single nands as explicit IC
    nand_ic = TI_CD4011BE()
    for ic_nand, xor_nand in zip(nand_ic.NODEs.nands, nxor.NODEs.nands):
        specialize_module(xor_nand, ic_nand)

    app.NODEs.nand_ic = nand_ic

    # export
    logger.info("Make graph")
    G = app.get_graph()

    logger.info("Make netlist")
    t1 = make_t1_netlist_from_graph(G)
    t2 = make_t2_netlist_from_t1(t1)
    netlist = from_faebryk_t2_netlist(t2)

    # from pretty import pretty
    # logger.info("Experiment components")
    # logger.info("\n" + "\n".join(pretty(c) for c in components))
    export_netlist(netlist)

    if make_graph:
        logger.info("Make render")
        render_matrix(
            G.G,
            nodes_rows=[
                [nand_ic, led, nxor, xor, e_out],
            ],
            depth=1,
            show_full=False,
            show_non_sum=False,
        ).show()
        # export_graph(G.G, False)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running experiment")

    typer.run(main)
