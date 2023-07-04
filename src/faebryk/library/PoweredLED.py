# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.LED import LED
from faebryk.library.Resistor import Resistor
from faebryk.library.TBD import TBD


class PoweredLED(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            power = ElectricPower()

        self.IFs = _IFs(self)

        self.IFs.power.NODEs.hv.connect(self.NODEs.led.IFs.anode)

        class _NODEs(Module.NODES()):
            current_limiting_resistor = Resistor(TBD())
            led = LED()

        self.NODEs = _NODEs(self)

        self.IFs.power.NODEs.hv.connect(self.NODEs.led.IFs.anode)
        self.IFs.power.NODEs.lv.connect_via(
            self.NODEs.current_limiting_resistor, self.NODEs.led.IFs.cathode
        )
