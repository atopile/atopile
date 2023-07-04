# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from faebryk.core.core import Module
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.power_switch import PowerSwitch
from faebryk.library.powered_led import PoweredLED


class LEDIndicator(Module):
    def __init__(self, logic_low: bool, normally_on: bool) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            logic_in = ElectricLogic()
            power_in = ElectricPower()

        self.IFs = _IFs(self)

        # components
        class _CMPs(Module.NODES()):
            led = PoweredLED()
            power_switch = PowerSwitch(
                lowside=not logic_low, normally_closed=normally_on
            )

        self.CMPs = _CMPs(self)

        #
        self.IFs.power_in.connect_via(self.CMPs.power_switch, self.CMPs.led.IFs.power)
        self.CMPs.power_switch.IFs.logic_in.connect(self.IFs.logic_in)
