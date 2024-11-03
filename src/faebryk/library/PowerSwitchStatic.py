# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import faebryk.library._F as F
from faebryk.libs.picker.picker import has_part_picked_remove


class PowerSwitchStatic(F.PowerSwitch):
    """
    A power switch that bridges power through statically

    This is useful when transforming an F.ElectricLogic to an F.ElectricPower
    """

    picked: has_part_picked_remove

    def __init__(self) -> None:
        super().__init__(normally_closed=False)

    def __preinit__(self):
        self.power_in.connect(self.switched_power_out)
        self.logic_in.reference.connect(self.power_in)
        self.logic_in.set(True)
