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

    # TODO make generic
    power_switch = L.f_field(F.PowerSwitchMOSFET)(lowside=True, normally_closed=False)

    def __preinit__(self):
        self.power_in.connect_via(self.power_switch, self.led.power)
        self.power_switch.logic_in.connect(self.logic_in)
