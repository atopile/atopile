# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import cast_assert


class ElectricPower(F.Power):
    class can_be_decoupled_power(F.can_be_decoupled.impl()):
        def decouple(
            self,
            owner: Module,
            count: int = 1,
        ):
            obj = self.get_obj(ElectricPower)

            capacitor = F.MultiCapacitor(count)

            # FIXME seems to cause contradictions
            capacitor.max_voltage.constrain_ge(obj.voltage * 1.5)

            obj.hv.connect_via(capacitor, obj.lv)

            name = f"decoupling_{obj.get_name(accept_no_parent=True)}"
            new_capacitor = capacitor
            # Merge
            if obj.has_trait(F.is_decoupled):
                old_capacitor = obj.get_trait(F.is_decoupled).capacitor
                capacitor = F.MultiCapacitor.from_capacitors(
                    old_capacitor,
                    new_capacitor,
                )
                name = old_capacitor.get_name(accept_no_parent=True) + "'"

            # TODO improve
            if name in owner.runtime:
                name += "_"
            owner.add(capacitor, name=name)
            obj.add(F.is_decoupled(capacitor))

            return new_capacitor

    class can_be_surge_protected_power(F.can_be_surge_protected.impl()):
        def protect(self, owner: Module):
            obj = self.get_obj(ElectricPower)
            surge_protection = F.SurgeProtection.from_interfaces(obj.lv, obj.hv)
            owner.add(
                surge_protection,
                name=f"surge_protection_{obj.get_name(accept_no_parent=True)}",
            )
            obj.add(F.is_surge_protected_defined(surge_protection))
            return surge_protection

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
