# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class Button(Module):
    unnamed = L.list_field(2, F.Electrical)
    height = L.p_field(
        units=P.mm,
        likely_constrained=False,
        soft_set=L.Range(1 * P.mm, 10 * P.mm),
        tolerance_guess=10 * P.percent,
    )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.S
    )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.unnamed[0], self.unnamed[1])
