# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from faebryk.core.core import Module
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.PoweredLED import PoweredLED
from p1_splitter.libtemp import PowerSwitch


class LEDIndicator(Module):
    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            logic_in = ElectricLogic()
            power_in = ElectricPower()

        self.IFs = _IFs(self)

        # components
        class _NODEs(Module.NODES()):
            led = PoweredLED()
            power_switch = PowerSwitch()

        self.NODEs = _NODEs(self)

        self.IFs.power_in.connect_via(self.NODEs.power_switch, self.NODEs.led.IFs.power)
        self.NODEs.power_switch.IFs.logic_in.connect(self.IFs.logic_in)
