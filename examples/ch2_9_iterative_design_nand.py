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

import faebryk.library._F as F
from faebryk.core.graph import GraphFunctions
from faebryk.core.module import Module
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class PowerSource(Module):
    power: F.ElectricPower


class XOR_with_NANDS(F.LogicGates.XOR):
    nands = L.list_field(4, lambda: F.LogicGates.NAND(2))

    def __init__(self):
        super().__init__(2)

    def __preinit__(self):
        A = self.inputs[0]
        B = self.inputs[1]

        G = self.nands
        Q = self.outputs[0]

        # ~(a&b)
        q0 = G[0].get_trait(F.LogicOps.can_logic_nand).nand(A, B)
        # ~(a&~b)
        q1 = G[1].get_trait(F.LogicOps.can_logic_nand).nand(A, q0)
        # ~(~a&b)
        q2 = G[2].get_trait(F.LogicOps.can_logic_nand).nand(B, q0)
        # (a&~b) o| (~a&b)
        q3 = G[3].get_trait(F.LogicOps.can_logic_nand).nand(q1, q2)

        Q.connect(q3)


class App(Module):
    def __preinit__(self) -> None:
        super().__preinit__()

        # levels
        on = F.Logic()
        off = F.Logic()

        # power
        power_source = PowerSource()

        # alias
        power = power_source.power

        # logic
        logic_in = F.Logic()
        logic_out = F.Logic()

        xor = F.LogicGates.XOR(2)
        logic_out.connect(xor.get_trait(F.LogicOps.can_logic_xor).xor(logic_in, on))

        # led
        led = F.LEDIndicator(use_mosfet=True)
        led.power_in.connect(power)

        # application
        switch = F.Switch(F.Logic)()

        logic_in.connect_via(switch, on)

        # bring logic signals into electrical domain
        e_in = logic_in.specialize(F.ElectricLogic())
        e_out = logic_out.specialize(F.ElectricLogic())
        e_on = on.specialize(F.ElectricLogic())
        e_off = off.specialize(F.ElectricLogic())
        e_in.reference.connect(power)
        e_out.reference.connect(power)
        e_on.reference.connect(power)
        e_off.reference.connect(power)
        e_in.set_weak(on=False, owner=self)
        e_on.set(on=True)
        e_off.set(on=False)

        e_out.connect(led.logic_in)

        nxor = xor.specialize(XOR_with_NANDS())
        battery = power_source.specialize(F.Battery())

        el_switch = switch.specialize(F.Switch(F.ElectricLogic)())
        e_switch = F.Switch(F.Electrical)()
        e_switch = el_switch.specialize(
            e_switch,
            matrix=[(e, el.line) for e, el in zip(e_switch.unnamed, el_switch.unnamed)],
        )
        e_switch.add(
            F.has_explicit_part.by_supplier(
                "C318884",
                pinmap={
                    "1": e_switch.unnamed[0],
                    "2": e_switch.unnamed[0],
                    "3": e_switch.unnamed[1],
                    "4": e_switch.unnamed[1],
                },
            )
        )

        # build graph
        for c in [
            led,
            switch,
            battery,
            e_switch,
        ]:
            self.add(c)

        # parametrizing
        for _, t in GraphFunctions(self.get_graph()).nodes_with_trait(
            F.ElectricLogic.has_pulls
        ):
            for pull_resistor in (r for r in t.get_pulls() if r):
                pull_resistor.resistance.constrain_subset(
                    L.Range.from_center_rel(100 * P.kohm, 0.05)
                )
        power_source.power.voltage.constrain_subset(
            L.Range.from_center_rel(3 * P.V, 0.05)
        )
        led.led.led.brightness.constrain_subset(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
        )

        # packages single nands as explicit IC
        nand_ic = F.TI_CD4011BE()
        for ic_nand, xor_nand in zip(nand_ic.gates, nxor.nands):
            xor_nand.specialize(ic_nand)

        # connect power to IC
        nand_ic.power.connect(power_source.power)

        self.add(nand_ic)

        # TODO: remove when we have a LED picker
        led.led.led.add(F.has_explicit_part.by_supplier("C965802"))
        led.led.led.forward_voltage.alias_is(2.4 * P.V)
        led.led.led.max_brightness.alias_is(435 * P.millicandela)
        led.led.led.max_current.alias_is(20 * P.mA)
        led.led.led.color.alias_is(F.LED.Color.YELLOW)

        # TODO remove when we have a battery picker
        battery.add(
            F.has_explicit_part.by_supplier(
                "C5239862",
                pinmap={
                    "1": battery.power.lv,
                    "2": battery.power.hv,
                },
            )
        )
        battery.voltage.alias_is(3 * P.V)

        # TODO remove when we have a MOSFET picker
        mosfet = led.get_children_modules(types=F.MOSFET).pop()
        mosfet.add(F.has_explicit_part.by_supplier("C5364305"))
        mosfet.channel_type.alias_is(F.MOSFET.ChannelType.N_CHANNEL)
        mosfet.saturation_type.alias_is(F.MOSFET.SaturationType.ENHANCEMENT)
