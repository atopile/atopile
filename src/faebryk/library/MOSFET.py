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

    # @L.rt_field
    # def pickable(self) -> F.is_pickable_by_type:
    #     return F.is_pickable_by_type(
    #         F.is_pickable_by_type.Type.MOSFET,
    #         {
    #             "channel_type": self.channel_type,
    #             # TODO: add support in backend
    #             # "saturation_type": self.saturation_type,
    #             "gate_source_threshold_voltage": self.gate_source_threshold_voltage,
    #             "max_drain_source_voltage": self.max_drain_source_voltage,
    #             "max_continuous_drain_current": self.max_continuous_drain_current,
    #             "on_resistance": self.on_resistance,
    #         },
    #     )

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

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.source.add(F.has_net_name("source", level=F.has_net_name.Level.SUGGESTED))
        self.gate.add(F.has_net_name("gate", level=F.has_net_name.Level.SUGGESTED))
        self.drain.add(F.has_net_name("drain", level=F.has_net_name.Level.SUGGESTED))

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import MOSFET, ElectricLogic, ElectricPower

        mosfet = new MOSFET
        mosfet.channel_type = MOSFET.ChannelType.N_CHANNEL
        mosfet.saturation_type = MOSFET.SaturationType.ENHANCEMENT
        mosfet.gate_source_threshold_voltage = 2.5V +/- 10%
        mosfet.max_drain_source_voltage = 60V
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
