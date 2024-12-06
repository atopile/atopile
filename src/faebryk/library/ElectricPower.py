# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import cast_assert


class ElectricPower(F.Power):
    class can_be_decoupled_power(F.can_be_decoupled.impl()):
        def decouple(self):
            obj = self.get_obj(ElectricPower)

            capacitor = obj.add(F.Capacitor())
            capacitor.max_voltage.constrain_ge(obj.voltage * 1.5)

            obj.hv.connect_via(capacitor, obj.lv)

            obj.add(F.is_decoupled(capacitor))
            return capacitor

        def is_implemented(self):
            return not self.obj.has_trait(F.is_decoupled)

    class can_be_surge_protected_power(F.can_be_surge_protected.impl()):
        def on_obj_set(self):
            obj = self.get_obj(ElectricPower)
            self.lv = obj.lv
            self.hv = obj.hv

        def protect(self):
            obj = self.get_obj(ElectricPower)
            return [
                tvs.builder(lambda t: t.reverse_working_voltage.alias_is(obj.voltage))
                for tvs in F.can_be_surge_protected_defined.protect(self)
            ]

    hv: F.Electrical
    lv: F.Electrical

    voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        domain=L.Domains.Numbers.REAL(),
        soft_set=L.Range(0 * P.V, 1000 * P.V),
        tolerance_guess=5 * P.percent,
    )
    max_current = L.p_field(units=P.A)
    """
    Only for this particular power interface
    Does not propagate to connections
    """

    surge_protected: can_be_surge_protected_power
    decoupled: can_be_decoupled_power

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(self)

    def fused(self, attach_to: Node | None = None):
        fused_power = type(self)()
        fuse = fused_power.add(F.Fuse())

        fused_power.hv.connect_via(fuse, self.hv)
        fused_power.lv.connect(self.lv)

        self.connect_shallow(fused_power)

        fuse.trip_current.constrain_subset(
            self.max_current * L.Range.from_center_rel(1.0, 0.1)
        )
        fused_power.max_current.constrain_le(fuse.trip_current)

        if attach_to is not None:
            attach_to.add(fused_power)

        return fused_power

    def __preinit__(self) -> None:
        ...
        # self.voltage.alias_is(
        #    self.hv.potential - self.lv.potential
        # )
        self.voltage.add(
            F.is_dynamic_by_connections(
                lambda mif: cast_assert(ElectricPower, mif).voltage
            )
        )
