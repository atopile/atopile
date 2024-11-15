# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class Common_Mode_Filter(Module):
    coil_a: F.Inductor
    coil_b: F.Inductor

    inductance: F.TBD
    self_resonant_frequency: F.TBD
    rated_current: F.TBD
    dc_resistance: F.TBD

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.FL
    )

    def __preinit__(self):
        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        for coil in [self.coil_a, self.coil_b]:
            coil.inductance.merge(self.inductance)
            coil.self_resonant_frequency.merge(self.self_resonant_frequency)
            coil.rated_current.merge(self.rated_current)
            coil.dc_resistance.merge(self.dc_resistance)
