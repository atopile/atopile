# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import faebryk.library._F as F


class PowerSwitchStatic(F.PowerSwitch):
    """
    A power switch that bridges power through statically

    This is useful when transforming an F.ElectricLogic to an F.ElectricPower
    """

    picked: F.has_part_removed

    def __init__(self, normally_closed: bool) -> None:
        super().__init__(normally_closed=normally_closed)

    def __preinit__(self):
        self.power_in.connect(self.switched_power_out)
        if self._normally_closed:
            self.logic_in.reference.hv.connect(self.power_in.hv)
            self.logic_in.line.connect(self.power_in.lv)
        else:
            self.logic_in.reference.lv.connect(self.power_in.lv)
            self.logic_in.line.connect(self.power_in.hv)
        self.logic_in.reference.voltage.constrain_subset(self.power_in.voltage)
