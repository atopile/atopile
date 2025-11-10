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

    channel_type = F.Parameters.EnumParameter.MakeChild(enum_t=ChannelType)
    saturation_type = F.Parameters.EnumParameter.MakeChild(enum_t=SaturationType)
    gate_source_threshold_voltage = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Volt
    )
    max_drain_source_voltage = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Volt
    )
    max_continuous_drain_current = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Ampere
    )
    on_resistance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)

    source = F.Electrical.MakeChild()
    gate = F.Electrical.MakeChild()
    drain = F.Electrical.MakeChild()

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.Q
    )

    _can_bridge = F.can_bridge.MakeChild(in_=source, out_=drain)

    _pin_association_heuristic = F.has_pin_association_heuristic.MakeChild(
        mapping={
            source: ["S", "Source"],
            gate: ["G", "Gate"],
            drain: ["D", "Drain"],
        },
        accept_prefix=False,
        case_sensitive=False,
    )

    S = F.has_simple_value_representation.Spec
    _simple_repr = F.has_simple_value_representation.MakeChild(
        S(gate_source_threshold_voltage, prefix="Vgs"),
        S(max_drain_source_voltage, prefix="Vds max"),
        S(max_continuous_drain_current, prefix="Id max"),
        S(on_resistance, prefix="Ron"),
    )
    # TODO: add trait
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
