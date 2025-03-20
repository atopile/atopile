# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class Inductor(Module):
    unnamed = L.list_field(2, F.Electrical)

    inductance = L.p_field(
        units=P.H,
        likely_constrained=True,
        soft_set=L.Range(100 * P.nH, 1 * P.H),
        tolerance_guess=10 * P.percent,
    )
    self_resonant_frequency = L.p_field(
        units=P.Hz,
        likely_constrained=True,
        soft_set=L.Range(100 * P.kHz, 1 * P.GHz),
        tolerance_guess=10 * P.percent,
    )
    max_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(1 * P.mA, 100 * P.A),
    )
    dc_resistance = L.p_field(
        units=P.Ω,
        soft_set=L.Range(10 * P.mΩ, 100 * P.Ω),
        tolerance_guess=10 * P.percent,
    )

    # @L.rt_field
    # def pickable(self) -> F.is_pickable_by_type:
    #     return F.is_pickable_by_type(
    #         F.is_pickable_by_type.Type.Inductor,
    #         {
    #             "inductance": self.inductance,
    #             "self_resonant_frequency": self.self_resonant_frequency,
    #             "max_current": self.max_current,
    #             "dc_resistance": self.dc_resistance,
    #         },
    #     )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.unnamed)

    attach_to_footprint: F.can_attach_to_footprint_symmetrically

    @L.rt_field
    def simple_value_representation(self):
        S = F.has_simple_value_representation_based_on_params_chain.Spec
        return F.has_simple_value_representation_based_on_params_chain(
            S(self.inductance, tolerance=True),
            S(self.self_resonant_frequency),
            S(self.max_current),
            S(self.dc_resistance),
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.L
    )

    # TODO: remove @https://github.com/atopile/atopile/issues/727
    @property
    def p1(self) -> F.Electrical:
        """Signal to one side of the inductor."""
        return self.unnamed[0]

    @property
    def p2(self) -> F.Electrical:
        """Signal to the other side of the inductor."""
        return self.unnamed[1]
