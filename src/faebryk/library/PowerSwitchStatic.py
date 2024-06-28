# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.PowerSwitch import PowerSwitch


class PowerSwitchStatic(PowerSwitch):
    """
    A power switch that bridges power through statically

    This is useful when transforming an ElectricLogic to an ElectricPower
    """

    def __init__(self) -> None:
        super().__init__(normally_closed=False)

        self.IFs.power_in.connect(self.IFs.switched_power_out)
        self.IFs.logic_in.connect_reference(self.IFs.power_in)
        self.IFs.logic_in.set(True)
