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

import faebryk.library._F as F
from faebryk.core.core import Module
from faebryk.core.util import (
    get_all_nodes_with_trait,
    specialize_interface,
    specialize_module,
)
from faebryk.library._F import Constant
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.examples.buildutil import apply_design_to_pcb
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.units import P
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class PowerSource(Module):
    def __init__(self) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            power = F.ElectricPower()

        self.IFs = IFS(self)


class XOR_with_NANDS(F.LogicGates.XOR):
    def __init__(
        self,
    ):
        super().__init__(Constant(2))

        class NODES(Module.NODES()):
            nands = times(4, lambda: F.LogicGates.NAND(Constant(2)))

        self.NODEs = NODES(self)

        A = self.IFs.inputs[0]
        B = self.IFs.inputs[1]

        G = self.NODEs.nands
        Q = self.IFs.outputs[0]

        # ~(a&b)
        q0 = G[0].get_trait(F.LogicOps.can_logic_nand).nand(A, B)
        # ~(a&~b)
        q1 = G[1].get_trait(F.LogicOps.can_logic_nand).nand(A, q0)
        # ~(~a&b)
        q2 = G[2].get_trait(F.LogicOps.can_logic_nand).nand(B, q0)
        # (a&~b) o| (~a&b)
        q3 = G[3].get_trait(F.LogicOps.can_logic_nand).nand(q1, q2)

        Q.connect(q3)


def App():
    # levels
    on = F.Logic()
    off = F.Logic()

    # power
    power_source = PowerSource()

    # alias
    power = power_source.IFs.power

    # logic
    logic_in = F.Logic()
    logic_out = F.Logic()

    xor = F.LogicGates.XOR(Constant(2))
    logic_out.connect(xor.get_trait(F.LogicOps.can_logic_xor).xor(logic_in, on))

    # led
    led = F.LEDIndicator()
    led.IFs.power_in.connect(power)

    # application
    switch = F.Switch(F.Logic)()

    logic_in.connect_via(switch, on)

    # bring logic signals into electrical domain
    e_in = specialize_interface(logic_in, F.ElectricLogic())
    e_out = specialize_interface(logic_out, F.ElectricLogic())
    e_on = specialize_interface(on, F.ElectricLogic())
    e_off = specialize_interface(off, F.ElectricLogic())
    e_in.IFs.reference.connect(power)
    e_out.IFs.reference.connect(power)
    e_on.IFs.reference.connect(power)
    e_off.IFs.reference.connect(power)
    e_in.set_weak(on=False)
    e_on.set(on=True)
    e_off.set(on=False)

    e_out.connect(led.IFs.logic_in)

    nxor = specialize_module(xor, XOR_with_NANDS())
    battery = specialize_module(power_source, F.Battery())

    el_switch = specialize_module(switch, F.Switch(F.ElectricLogic)())
    e_switch = F.Switch(F.Electrical)()
    e_switch = specialize_module(
        el_switch,
        e_switch,
        matrix=[
            (e, el.IFs.signal)
            for e, el in zip(e_switch.IFs.unnamed, el_switch.IFs.unnamed)
        ],
    )

    # build graph
    app = Module()
    app.NODEs.components = [
        led,
        switch,
        battery,
        e_switch,
    ]

    # parametrizing
    for _, t in get_all_nodes_with_trait(app.get_graph(), F.ElectricLogic.has_pulls):
        for pull_resistor in (r for r in t.get_pulls() if r):
            pull_resistor.PARAMs.resistance.merge(100 * P.kohm)
    power_source.IFs.power.PARAMs.voltage.merge(3 * P.V)
    led.NODEs.led.NODEs.led.PARAMs.brightness.merge(
        TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
    )

    # packages single nands as explicit IC
    nand_ic = F.TI_CD4011BE()
    for ic_nand, xor_nand in zip(nand_ic.NODEs.gates, nxor.NODEs.nands):
        specialize_module(xor_nand, ic_nand)

    app.NODEs.nand_ic = nand_ic

    return app


# Boilerplate -----------------------------------------------------------------


def main():
    logger.info("Building app")
    app = App()

    logger.info("Export")
    apply_design_to_pcb(app)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running example")

    typer.run(main)
