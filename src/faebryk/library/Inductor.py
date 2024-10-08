# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import join_if_non_empty


class Inductor(Module):
    unnamed = L.list_field(2, F.Electrical)

    inductance = L.p_field(
        unit=P.H,
        likely_constrained=True,
        soft_set=L.Range(100 * P.nH, 1 * P.H),
        tolerance_guess=10 * P.percent,
    )
    self_resonant_frequency = L.p_field(
        unit=P.Hz,
        likely_constrained=True,
        soft_set=L.Range(100 * P.kHz, 1 * P.GHz),
        tolerance_guess=10 * P.percent,
    )
    rated_current = L.p_field(
        unit=P.A,
        likely_constrained=True,
        soft_set=L.Range(1 * P.mA, 100 * P.A),
        tolerance_guess=10 * P.percent,
    )
    dc_resistance = L.p_field(
        unit=P.Ω,
        soft_set=L.Range(10 * P.mΩ, 100 * P.Ω),
        tolerance_guess=10 * P.percent,
    )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.unnamed)

    attach_to_footprint: F.can_attach_to_footprint_symmetrically

    @L.rt_field
    def simple_value_representation(self):
        return F.has_simple_value_representation_based_on_params(
            (
                self.inductance,
                self.self_resonant_frequency,
                self.rated_current,
                self.dc_resistance,
            ),
            lambda inductance,
            self_resonant_frequency,
            rated_current,
            dc_resistance: join_if_non_empty(
                " ",
                inductance.as_unit_with_tolerance("H"),
                self_resonant_frequency.as_unit("Hz"),
                rated_current.as_unit("A"),
                dc_resistance.as_unit("Ω"),
            ),
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.L
    )
