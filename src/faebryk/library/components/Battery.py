# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
import faebryk.libs.library.L as L
from faebryk.core.module import Module
from faebryk.libs.units import P


class Battery(Module):
    voltage = L.p_field(
        units=P.V,
        soft_set=L.Range(0 * P.V, 100 * P.V),
        likely_constrained=True,
    )
    capacity = L.p_field(
        units=P.Ah,
        soft_set=L.Range(100 * P.mAh, 100 * P.Ah),
        likely_constrained=True,
    )

    power: F.ElectricPower

    def __preinit__(self) -> None:
        self.power.voltage.constrain_subset(self.voltage)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(self.power)

    designator = L.f_field(F.has_designator_prefix)("BAT")
