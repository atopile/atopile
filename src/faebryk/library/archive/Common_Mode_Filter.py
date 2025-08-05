# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class Common_Mode_Filter(Module):
    coil_a: F.Inductor
    coil_b: F.Inductor

    inductance = L.p_field(
        units=P.H,
        likely_constrained=True,
        soft_set=L.Range(1 * P.µH, 10 * P.mH),
        tolerance_guess=10 * P.percent,
    )
    self_resonant_frequency = L.p_field(
        units=P.Hz,
        likely_constrained=True,
        soft_set=L.Range(100 * P.Hz, 1 * P.MHz),
        tolerance_guess=10 * P.percent,
    )
    max_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(1 * P.A, 10 * P.A),
    )
    dc_resistance = L.p_field(
        units=P.Ω,
    )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.FL
    )

    def __preinit__(self):
        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        for coil in [self.coil_a, self.coil_b]:
            coil.inductance.alias_is(self.inductance)
            coil.self_resonant_frequency.alias_is(self.self_resonant_frequency)
            coil.max_current.alias_is(self.max_current)
            coil.dc_resistance.alias_is(self.dc_resistance)
