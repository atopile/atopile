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

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Common_Mode_Filter, Electrical

        module UsageExample:
            # Differential signal lines
            signal_p = new Electrical
            signal_n = new Electrical
            filtered_p = new Electrical  
            filtered_n = new Electrical
            
            cmf = new Common_Mode_Filter
            cmf.inductance = 100µH +/- 20%
            cmf.max_current = 500mA
            cmf.self_resonant_frequency = 10MHz +/- 20%
            
            # Connect the differential pair through the common mode filter
            signal_p ~ cmf.coil_a.unnamed[0]
            cmf.coil_a.unnamed[1] ~ filtered_p
            signal_n ~ cmf.coil_b.unnamed[0]  
            cmf.coil_b.unnamed[1] ~ filtered_n
        """,
        language=F.has_usage_example.Language.ato,
    )
