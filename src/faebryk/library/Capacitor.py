# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import IntEnum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import Quantity

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

    capacitance: F.TBD[Quantity]
    rated_voltage: F.TBD[Quantity]
    temperature_coefficient: F.TBD[TemperatureCoefficient]

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    designator_prefix = L.f_field(F.has_designator_prefix_defined)("C")

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.unnamed)

    @L.rt_field
    def simple_value_representation(self):
        from faebryk.core.util import (
            as_unit,
            as_unit_with_tolerance,
            enum_parameter_representation,
        )

        return F.has_simple_value_representation_based_on_params(
            (
                self.capacitance,
                self.rated_voltage,
                self.temperature_coefficient,
            ),
            lambda ps: " ".join(
                filter(
                    None,
                    [
                        as_unit_with_tolerance(ps[0], "F"),
                        as_unit(ps[1], "V"),
                        enum_parameter_representation(ps[2].get_most_narrow()),
                    ],
                )
            ),
        )
