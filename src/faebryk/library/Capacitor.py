# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P, Quantity

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
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.C
    )

    pickable = L.f_field(F.is_pickable_by_type)(F.is_pickable_by_type.Type.Capacitor)

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
        footprint: str | None = None,
    ):
        if nominal_capacitance is not None:
            if tolerance is None:
                tolerance = 0.2
            capacitance = L.Range.from_center_rel(nominal_capacitance, tolerance)
            self.capacitance.constrain_subset(capacitance)

        if footprint is not None:
            self.attach_to_footprint.add(F.has_package_requirement(footprint))
