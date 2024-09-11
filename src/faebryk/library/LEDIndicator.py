# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class LEDIndicator(Module):
    # interfaces

    logic_in: F.ElectricLogic
    power_in: F.ElectricPower

    # components

    led: F.PoweredLED

    power_switch = L.f_field(F.PowerSwitch)(normally_closed=False)

    def __init__(self, use_mosfet: bool = True):
        self._use_mosfet = use_mosfet

    def __preinit__(self):
        self.power_in.connect_via(self.power_switch, self.led.power)
        self.power_switch.logic_in.connect(self.logic_in)

        if self._use_mosfet:
            self.power_switch.specialize(
                F.PowerSwitchMOSFET(lowside=True, normally_closed=False)
            )
        else:
            self.power_switch.specialize(F.PowerSwitchStatic())
