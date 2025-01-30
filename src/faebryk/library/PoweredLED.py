# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class PoweredLED(Module):
    power: F.ElectricPower

    led: F.LED
    current_limiting_resistor: F.Resistor

    def __preinit__(self):
        self.power.hv.connect_via(
            [self.led, self.current_limiting_resistor], self.power.lv
        )

        self.current_limiting_resistor.resistance.alias_is(
            (self.power.voltage - self.led.forward_voltage) / self.led.current
        )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.power.hv, self.power.lv)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(self.power)
