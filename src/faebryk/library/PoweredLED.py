# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class PoweredLED(Module):
    power: F.ElectricPower
    current_limiting_resistor: F.Resistor
    led: F.LED

    def __preinit__(self):
        self.power.hv.connect(self.led.anode)
        self.led.connect_via_current_limiting_resistor_to_power(
            self.current_limiting_resistor,
            self.power,
            low_side=True,
        )
        self.current_limiting_resistor.allow_removal_if_zero()

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.power.hv, self.power.lv)
