# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import IntEnum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import join_if_non_empty

logger = logging.getLogger(__name__)


class Capacitor(Module):
    class TemperatureCoefficient(IntEnum):
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
        unit=P.F,
        likely_constrained=True,
        soft_set=L.Range(100 * P.pF, 1 * P.F),
        tolerance_guess=10 * P.percent,
    )
    rated_voltage = L.p_field(
        unit=P.V,
        likely_constrained=True,
        soft_set=L.Range(10 * P.V, 100 * P.V),
        tolerance_guess=10 * P.percent,
    )
    temperature_coefficient = L.p_field(
        domain=L.Domains.ENUM(TemperatureCoefficient),
    )

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.C
    )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.unnamed)

    @L.rt_field
    def simple_value_representation(self):
        return F.has_simple_value_representation_based_on_params(
            (
                self.capacitance,
                self.rated_voltage,
                self.temperature_coefficient,
            ),
            lambda c, v, t: join_if_non_empty(
                " ",
                c.as_unit_with_tolerance("F"),
                v.as_unit("V"),
                t.enum_parameter_representation(),
            ),
        )
