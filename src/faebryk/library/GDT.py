# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class GDT(Module):
    common: F.Electrical
    tube_1: F.Electrical
    tube_2: F.Electrical

    dc_breakdown_voltage: F.TBD
    impulse_discharge_current: F.TBD

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.tube_1, self.tube_2)

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.GDT
    )
