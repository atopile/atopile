# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

import faebryk.core.node as fabll
import faebryk.library._F as F


class MOSFET(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    class ChannelType(StrEnum):
        N_CHANNEL = "N_CHANNEL"
        P_CHANNEL = "P_CHANNEL"

    class SaturationType(StrEnum):
        ENHANCEMENT = "ENHANCEMENT"
        DEPLETION = "DEPLETION"

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    source = F.Electrical.MakeChild()
    gate = F.Electrical.MakeChild()
    drain = F.Electrical.MakeChild()

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

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    mapping = {
        source: ["source", "s"],
        gate: ["gate", "g"],
        drain: ["drain", "d"],
    }

    for e in [source, gate, drain]:
        lead = F.Lead.is_lead.MakeChild()
        e.add_dependant(fabll.Traits.MakeEdge(lead, [e]))
        lead.add_dependant(
            fabll.Traits.MakeEdge(
                F.Lead.can_attach_to_pad_by_name_heuristic.MakeChild(mapping[e]), [lead]
            )
        )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.Q)
    )

    _can_bridge = fabll.Traits.MakeEdge(F.can_bridge.MakeChild(in_=source, out_=drain))

    S = F.has_simple_value_representation.Spec
    _simple_repr = fabll.Traits.MakeEdge(
        F.has_simple_value_representation.MakeChild(
            S(gate_source_threshold_voltage, prefix="Vgs"),
            S(max_drain_source_voltage, prefix="Vds max"),
            S(max_continuous_drain_current, prefix="Id max"),
            S(on_resistance, prefix="Ron"),
        )
    )
    # TODO: add trait
    # self.source.add(F.has_net_name("source", level=F.has_net_name.Level.SUGGESTED))
    # self.gate.add(F.has_net_name("gate", level=F.has_net_name.Level.SUGGESTED))
    # self.drain.add(F.has_net_name("drain", level=F.has_net_name.Level.SUGGESTED))

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
        ).put_on_type()
    )
