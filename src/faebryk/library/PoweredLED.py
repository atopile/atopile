# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.LED import LED
from faebryk.library.Resistor import Resistor


class PoweredLED(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            power = ElectricPower()

        self.IFs = _IFs(self)

        class _NODEs(Module.NODES()):
            current_limiting_resistor = Resistor()
            led = LED()

        self.NODEs = _NODEs(self)

        self.IFs.power.IFs.hv.connect(self.NODEs.led.IFs.anode)
        self.NODEs.led.connect_via_current_limiting_resistor_to_power(
            self.NODEs.current_limiting_resistor,
            self.IFs.power,
            low_side=True,
        )

        self.add_trait(can_bridge_defined(self.IFs.power.IFs.hv, self.IFs.power.IFs.lv))
        self.NODEs.current_limiting_resistor.allow_removal_if_zero()
