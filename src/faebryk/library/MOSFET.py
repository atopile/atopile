# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class MOSFET(Module):
    class ChannelType(Enum):
        N_CHANNEL = auto()
        P_CHANNEL = auto()

    class SaturationType(Enum):
        ENHANCEMENT = auto()
        DEPLETION = auto()

    channel_type = L.p_field(domain=L.Domains.ENUM(ChannelType))
    saturation_type = L.p_field(domain=L.Domains.ENUM(SaturationType))
    gate_source_threshold_voltage = L.p_field(units=P.V)
    max_drain_source_voltage = L.p_field(units=P.V)
    max_continuous_drain_current = L.p_field(units=P.A)
    on_resistance = L.p_field(units=P.ohm)

    source: F.Electrical
    gate: F.Electrical
    drain: F.Electrical

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.Q
    )

    pickable = L.f_field(F.is_pickable_by_type)(F.is_pickable_by_type.Type.MOSFET)

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
