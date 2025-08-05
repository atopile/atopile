# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.core.parameter import Add
from faebryk.libs.library import L
from faebryk.libs.units import P


class ElectricPower(F.Power):
    """
    ElectricPower is a class that represents a power rail. Power rails have a
    higher potential (hv), and lower potential (lv) Electrical.
    """

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
    max_current = L.p_field(
        units=P.A,
        domain=L.Domains.Numbers.REAL(),
    )
    """
    WARNING!!!
    Only for this particular power interface
    Does not propagate to connections
    """
    bus_max_current_consumption_sum = L.p_field(
        units=P.A, domain=L.Domains.Numbers.REAL()
    )
    """
    Summed current for all connected power interfaces
    Only available after resolve_bus_parameters
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
        # TODO maybe better bus_consumption
        fused_power.max_current.constrain_le(fuse.trip_current)

        if attach_to is not None:
            attach_to.add(fused_power)

        return fused_power

    def __preinit__(self) -> None:
        ...
        # self.voltage.alias_is(
        #    self.hv.potential - self.lv.potential
        # )
        self.voltage.add(F.is_bus_parameter())
        self.bus_max_current_consumption_sum.add(
            F.is_bus_parameter(reduce=(self.max_current, Add))
        )

        self.lv.add(F.has_net_name("gnd"))

    @property
    def vcc(self) -> F.Electrical:
        """Higher-voltage side of the power interface."""
        return self.hv

    @property
    def gnd(self) -> F.Electrical:
        """Lower-voltage side of the power interface."""
        return self.lv

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        # Apply suffixes to the electrical lines of the signals
        self.hv.add(F.has_net_name("VCC", level=F.has_net_name.Level.SUGGESTED))
        self.lv.add(F.has_net_name("GND", level=F.has_net_name.Level.SUGGESTED))

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import ElectricPower

        power_5v = new ElectricPower
        assert power_5v.voltage within 5V +/- 5%
        assert power_5v.max_current <= 1A

        # Connect 2 ElectricPowers together
        power_5v ~ ic.power_input

        # Connect an example bypass capacitor
        power_5v.hv ~> example_capacitor ~> power_5v.lv
        """,
        language=F.has_usage_example.Language.ato,
    )
