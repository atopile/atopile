# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module  # noqa: F401
from faebryk.libs.library import L  # noqa: F401


class LEDIndicator(Module):
    # interfaces

    logic_in: F.ElectricLogic
    power_in: F.ElectricPower

    # components

    led: F.PoweredLED

    def __init__(self, use_mosfet: bool = False, active_low: bool = False):
        super().__init__()
        self._use_mosfet = use_mosfet
        self._active_low = active_low

    def __preinit__(self):
        if self._use_mosfet:
            power_switch = self.add(
                F.PowerSwitchMOSFET(lowside=True, normally_closed=self._active_low)
            )
        else:
            power_switch = self.add(
                F.PowerSwitchStatic(normally_closed=self._active_low)
            )

        self.power_in.connect_via(power_switch, self.led.power)
        power_switch.logic_in.connect(self.logic_in)
