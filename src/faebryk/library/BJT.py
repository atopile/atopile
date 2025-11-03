# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.node import rt_field


class BJT(fabll.Node):
    class DopingType(Enum):
        NPN = auto()
        PNP = auto()

    # TODO use this, here is more info: https://en.wikipedia.org/wiki/Bipolar_junction_transistor#Regions_of_operation
    class OperationRegion(Enum):
        ACTIVE = auto()
        INVERTED = auto()
        SATURATION = auto()
        CUT_OFF = auto()

    # doping_type = fabll.Parameter.MakeChild_Enum(enum_t=DopingType)
    # operation_region = fabll.Parameter.MakeChild_Enum(enum_t=OperationRegion)

    emitter = F.Electrical.MakeChild()
    base = F.Electrical.MakeChild()
    collector = F.Electrical.MakeChild()

    _can_bridge = F.can_bridge.MakeChild(in_=collector, out_=emitter)

    _pin_association_heuristic = F.has_pin_association_heuristic_lookup_table.MakeChild(
        mapping={
            emitter: ["E", "Emitter"],
            base: ["B", "Base"],
            collector: ["C", "Collector"],
        },
        accept_prefix=False,
        case_sensitive=False,
    )

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.Q
    ).put_on_type()

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import BJT, Resistor, ElectricPower

        bjt = new BJT
        bjt.doping_type ="NPN"
        bjt.mpn = "C373737

        # Use as amplifier with bias resistors
        base_resistor = new Resistor
        collector_resistor = new Resistor
        power_supply = new ElectricPower

        # Basic amplifier configuration
        power_supply.hv ~> collector_resistor ~> bjt.collector
        bjt.emitter ~ power_supply.lv
        input_signal ~> base_resistor ~> bjt.base
        output_signal ~ bjt.collector
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()
