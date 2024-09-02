# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.units import Quantity


class Battery(Module):
    voltage: F.TBD[Quantity]
    capacity: F.TBD[Quantity]

    power: F.ElectricPower

    def __preinit__(self) -> None:
        self.power.voltage.merge(self.voltage)
