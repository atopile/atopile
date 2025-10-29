# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class PoweredLED(fabll.Node):
    power = F.ElectricPower.MakeChild()
    current_limiting_resistor = F.Resistor.MakeChild()
    led = F.LED.MakeChild()

    def __init__(self, low_side_resistor: bool = True):
        super().__init__()
        self._low_side_resistor = low_side_resistor

    def __preinit__(self):
        if self._low_side_resistor:
            self.power.hv.connect_via(
                [self.led, self.current_limiting_resistor], self.power.lv
            )
        else:
            self.power.hv.connect_via(
                [self.current_limiting_resistor, self.led], self.power.lv
            )

        # I = (V - V_led) / R, rearranged to assist the solver to find a solution
        self.current_limiting_resistor.resistance.alias_is(
            (self.power.voltage - self.led.forward_voltage) / self.led.current
        )

        # help solver
        self.led.forward_voltage.constrain_le(self.power.voltage)
        self.led.forward_voltage.alias_is(
            self.power.voltage
            - self.led.current * self.current_limiting_resistor.resistance
        )

    _can_bridge = F.can_bridge.MakeChild(in_=power.nodetype.hv, out_=power.nodetype.lv)

    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(self.power)
