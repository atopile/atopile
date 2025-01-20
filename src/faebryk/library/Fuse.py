# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class Fuse(Module):
    class FuseType(Enum):
        NON_RESETTABLE = auto()
        RESETTABLE = auto()

    class ResponseType(Enum):
        SLOW = auto()
        FAST = auto()

    unnamed = L.list_field(2, F.Electrical)
    fuse_type = L.p_field(
        domain=L.Domains.ENUM(FuseType),
    )
    response_type = L.p_field(
        domain=L.Domains.ENUM(ResponseType),
    )
    trip_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        domain=L.Domains.Numbers.REAL(),
        soft_set=L.Range(100 * P.mA, 100 * P.A),
    )

    attach_to_footprint: F.can_attach_to_footprint_symmetrically

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.unnamed[0], self.unnamed[1])

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.F
    )
