# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F


class MOSFET(fabll.Node):
    class ChannelType(Enum):
        N_CHANNEL = auto()
        P_CHANNEL = auto()

    class SaturationType(Enum):
        ENHANCEMENT = auto()
        DEPLETION = auto()

    channel_type = fabll.Parameter.MakeChild_Enum(enum_t=ChannelType)
    saturation_type = fabll.Parameter.MakeChild_Enum(enum_t=SaturationType)
    gate_source_threshold_voltage = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Volt)
    max_drain_source_voltage = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Volt)
    max_continuous_drain_current = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Ampere
    )
    on_resistance = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Ohm)

    source = F.Electrical.MakeChild()
    gate = F.Electrical.MakeChild()
    drain = F.Electrical.MakeChild()

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.Q
    )

    _can_bridge = F.can_bridge.MakeChild(in_=source, out_=drain)

    pin_association_heuristic = F.has_pin_association_heuristic_lookup_table.MakeChild(
        mapping={
            source: ["S", "Source"],
            gate: ["G", "Gate"],
            drain: ["D", "Drain"],
        },
        accept_prefix=False,
        case_sensitive=False,
    )

    # self.source.add(F.has_net_name("source", level=F.has_net_name.Level.SUGGESTED))
    # self.gate.add(F.has_net_name("gate", level=F.has_net_name.Level.SUGGESTED))
    # self.drain.add(F.has_net_name("drain", level=F.has_net_name.Level.SUGGESTED))

    usage_example = F.has_usage_example.MakeChild(
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
