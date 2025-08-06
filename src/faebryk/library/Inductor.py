# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class Inductor(Module):
    terminals = L.list_field(2, F.Electrical)

    inductance = L.p_field(
        units=P.H,
        likely_constrained=True,
        soft_set=L.Range(100 * P.nH, 1 * P.H),
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
    self_resonant_frequency = L.p_field(
        units=P.Hz,
        likely_constrained=True,
        soft_set=L.Range(100 * P.kHz, 1 * P.GHz),
        tolerance_guess=10 * P.percent,
    )
    saturation_current = L.p_field(units=P.A)

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    pickable: F.is_pickable_by_type

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.terminals)


    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.L
    )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Electrical, Inductor

        inductor = new Inductor
        inductor.inductance = 10uH +/- 10%
        inductor.package = "SMD5x5mm"
        assert inductor.max_current >= 2A
        assert inductor.dc_resistance = 50mohm +/- 20%
        assert inductor.self_resonant_frequency within 100MHz +/- 10%
        assert inductor.saturation_current >= 2A

        electrical1 = new Electrical
        electrical2 = new Electrical

        electrical1 ~ inductor.terminals[0]
        electrical2 ~ inductor.terminals[1]
        # OR
        electrical1 ~> inductor ~> electrical2
        """,
        language=F.has_usage_example.Language.ato,
    )
