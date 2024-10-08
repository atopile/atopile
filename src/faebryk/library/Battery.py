# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
import faebryk.libs.library.L as L
from faebryk.core.module import Module
from faebryk.libs.units import P


class Battery(Module):
    voltage = L.p_field(
        unit=P.V,
        soft_set=L.Range(0 * P.V, 100 * P.V),
        guess=3.7 * P.V,
        tolerance_guess=5 * P.percent,
        likely_constrained=True,
    )
    capacity = L.p_field(
        unit=P.Ah,
        soft_set=L.Range(100 * P.mAh, 100 * P.Ah),
        guess=1 * P.Ah,
        tolerance_guess=5 * P.percent,
        likely_constrained=True,
    )

    power: F.ElectricPower

    def __preinit__(self) -> None:
        self.power.voltage.alias_is(self.voltage)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(self.power)
