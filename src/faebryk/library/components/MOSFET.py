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
    
    @deprecated(reason="Use channel_type instead")
    saturation_type = L.p_field(domain=L.Domains.ENUM(SaturationType))
    @deprecated(reason="Use rated_gate_source_threshold_voltage instead")
    gate_source_threshold_voltage = L.p_field(units=P.V)
    @deprecated(reason="Use rated_max_drain_source_voltage instead")
    max_drain_source_voltage = L.p_field(units=P.V)
    @deprecated(reason="Use rated_max_continuous_drain_current instead")
    max_continuous_drain_current = L.p_field(units=P.A)
    @deprecated(reason="Use rated_on_resistance instead")
    on_resistance = L.p_field(units=P.ohm)

    rated_gate_source_threshold_voltage = L.p_field(units=P.V)
    rated_max_drain_source_voltage = L.p_field(units=P.V)
    rated_max_continuous_drain_current = L.p_field(units=P.A)
    rated_on_resistance = L.p_field(units=P.ohm)

    source: F.Electrical
    gate: F.Electrical
    drain: F.Electrical

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.Q
    )

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.MOSFETS,
            params=[self.channel_type, self.rated_gate_source_threshold_voltage, self.rated_max_drain_source_voltage, self.rated_max_continuous_drain_current, self.rated_on_resistance],
        )

    def __init__(self, channel_type: ChannelType = ChannelType.N_CHANNEL):
        super().__init__()
        self.channel_type = channel_type

    @L.rt_field #TODO: Change bridge direction based on channel type
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

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import MOSFET, ElectricLogic, ElectricPower

        mosfet = new MOSFET
        mosfet.channel_type = MOSFET.ChannelType.N_CHANNEL
        mosfet.gate_source_threshold_voltage = 2.5V +/- 10%
        mosfet.rated_max_drain_source_voltage = 60V
        mosfet.max_continuous_drain_current = 30A
        mosfet.on_resistance = 5mohm +/- 20%
        mosfet.package = "SOT-23"

        # Use as a switch
        gate_control = new ElectricLogic
        power_supply = new ElectricPower
        load = new ElectricLogic

        mosfet.gate ~ gate_control.line
        mosfet.source ~ power_supply.lv
        mosfet.drain ~ load.line
        """,
        language=F.has_usage_example.Language.ato,
    )
