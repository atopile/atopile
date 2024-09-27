# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import Quantity


class MOSFET(Module):
    class ChannelType(Enum):
        N_CHANNEL = auto()
        P_CHANNEL = auto()

    class SaturationType(Enum):
        ENHANCEMENT = auto()
        DEPLETION = auto()

    channel_type: F.TBD[ChannelType]
    saturation_type: F.TBD[SaturationType]
    gate_source_threshold_voltage: F.TBD[Quantity]
    max_drain_source_voltage: F.TBD[Quantity]
    max_continuous_drain_current: F.TBD[Quantity]
    on_resistance: F.TBD[Quantity]

    source: F.Electrical
    gate: F.Electrical
    drain: F.Electrical

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.Q
    )

    # TODO pretty confusing
    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(in_if=self.source, out_if=self.drain)

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.source: ["S", "Source"],
                self.gate: ["G", "Gate"],
                self.drain: ["D", "Drain"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )
