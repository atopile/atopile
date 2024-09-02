# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import math

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P, Quantity


class ElectricPower(F.Power):
    class can_be_decoupled_power(F.can_be_decoupled_defined):
        def __init__(self) -> None: ...

        def on_obj_set(self):
            obj = self.get_obj(ElectricPower)
            super().__init__(hv=obj.hv, lv=obj.lv)

        def decouple(self):
            obj = self.get_obj(ElectricPower)
            return (
                super()
                .decouple()
                .builder(
                    lambda c: c.rated_voltage.merge(
                        F.Range(obj.voltage * 2.0, math.inf * P.V)
                    )
                )
            )

    class can_be_surge_protected_power(F.can_be_surge_protected_defined):
        def __init__(self) -> None: ...

        def on_obj_set(self):
            obj = self.get_obj(ElectricPower)
            super().__init__(obj.lv, obj.hv)

        def protect(self):
            obj = self.get_obj(ElectricPower)
            return [
                tvs.builder(lambda t: t.reverse_working_voltage.merge(obj.voltage))
                for tvs in super().protect()
            ]

    hv: F.Electrical
    lv: F.Electrical

    voltage: F.TBD[Quantity]

    surge_protected: can_be_surge_protected_power
    decoupled: can_be_decoupled_power

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(self)

    def __preinit__(self) -> None:
        ...
        # self.voltage.merge(
        #    self.hv.potential - self.lv.potential
        # )

    def _on_connect(self, other: ModuleInterface) -> None:
        super()._on_connect(other)

        if not isinstance(other, ElectricPower):
            return

        self.voltage.merge(other.voltage)
