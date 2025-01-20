# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import rt_field
from faebryk.libs.library import L


class BJT(Module):
    class DopingType(Enum):
        NPN = auto()
        PNP = auto()

    # TODO use this, here is more info: https://en.wikipedia.org/wiki/Bipolar_junction_transistor#Regions_of_operation
    class OperationRegion(Enum):
        ACTIVE = auto()
        INVERTED = auto()
        SATURATION = auto()
        CUT_OFF = auto()

    doping_type = L.p_field(domain=L.Domains.ENUM(DopingType))
    operation_region = L.p_field(domain=L.Domains.ENUM(OperationRegion))

    emitter: F.Electrical
    base: F.Electrical
    collector: F.Electrical

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.Q
    )

    @rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.collector, self.emitter)

    @rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.emitter: ["E", "Emitter"],
                self.base: ["B", "Base"],
                self.collector: ["C", "Collector"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )
