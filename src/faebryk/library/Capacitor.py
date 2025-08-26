# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto
from typing import TYPE_CHECKING

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.smd import SMDSize
from faebryk.libs.units import P, Quantity

# FIXME: this has to go this way to avoid gen_F detecting a circular import
if TYPE_CHECKING:
    from faebryk.library.ElectricPower import ElectricPower

logger = logging.getLogger(__name__)


class Capacitor(Module):
    class TemperatureCoefficient(Enum):
        Y5V = auto()
        Z5U = auto()
        X7S = auto()
        X5R = auto()
        X6R = auto()
        X7R = auto()
        X8R = auto()
        C0G = auto()

    unnamed = L.list_field(2, F.Electrical)

    capacitance = L.p_field(
        units=P.F,
        likely_constrained=True,
        soft_set=L.Range(100 * P.pF, 1 * P.F),
        tolerance_guess=10 * P.percent,
    )
    # Voltage at which the design may be damaged
    max_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(10 * P.V, 100 * P.V),
    )
    temperature_coefficient = L.p_field(
        domain=L.Domains.ENUM(TemperatureCoefficient),
    )

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.C
    )

    @L.rt_field
    def pickable(self) -> F.is_pickable_by_type:
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.CAPACITORS,
            params=[self.capacitance, self.max_voltage, self.temperature_coefficient],
        )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.unnamed)

    @L.rt_field
    def simple_value_representation(self):
        S = F.has_simple_value_representation_based_on_params_chain.Spec
        return F.has_simple_value_representation_based_on_params_chain(
            S(self.capacitance, tolerance=True),
            S(self.max_voltage),
            S(self.temperature_coefficient),
        )

    def explicit(
        self,
        nominal_capacitance: Quantity | None = None,
        tolerance: float | None = None,
        size: SMDSize | None = None,
    ):
        if nominal_capacitance is not None:
            if tolerance is None:
                tolerance = 0.2
            capacitance = L.Range.from_center_rel(nominal_capacitance, tolerance)
            self.capacitance.constrain_subset(capacitance)

        if size is not None:
            self.add(F.has_package_requirements(size=size))

    # TODO: remove @https://github.com/atopile/atopile/issues/727
    @property
    def p1(self) -> F.Electrical:
        """One side of the capacitor."""
        return self.unnamed[0]

    @property
    def p2(self) -> F.Electrical:
        """The other side of the capacitor."""
        return self.unnamed[1]

    class _has_power(L.Trait.decless()):
        """
        This trait is used to add power interfaces to
        capacitors who use them, keeping the interfaces
        off caps which don't use it.

        Caps have power-interfaces when used with them.
        """

        def __init__(self, power: "ElectricPower") -> None:
            super().__init__()
            self.power = power

    @property
    def power(self) -> "ElectricPower":
        """An `ElectricPower` interface, which is connected to the capacitor."""
        # FIXME: this has to go this way to avoid gen_F detecting a circular import
        from faebryk.library.ElectricPower import ElectricPower

        if self.has_trait(self._has_power):
            power = self.get_trait(self._has_power).power
        else:
            power = ElectricPower()
            self.add(power, name="power_shim")
            power.hv.connect_via(self, power.lv)
            self.add(self._has_power(power))

        return power

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Capacitor

        capacitor = new Capacitor
        capacitor.capacitance = 100nF +/- 10%
        assert capacitor.max_voltage within 25V to 50V
        capacitor.package = "0603"

        electrical1 ~ capacitor.unnamed[0]
        electrical2 ~ capacitor.unnamed[1]
        # OR
        electrical1 ~> capacitor ~> electrical2
        """,
        language=F.has_usage_example.Language.ato,
    )
