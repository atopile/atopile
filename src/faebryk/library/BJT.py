# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F


class BJT(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    class DopingType(Enum):
        NPN = auto()
        PNP = auto()

    # TODO use this, here is more info: https://en.wikipedia.org/wiki/Bipolar_junction_transistor#Regions_of_operation
    class OperationRegion(Enum):
        ACTIVE = auto()
        INVERTED = auto()
        SATURATION = auto()
        CUT_OFF = auto()

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    emitter = F.Electrical.MakeChild()
    base = F.Electrical.MakeChild()
    collector = F.Electrical.MakeChild()

    doping_type = F.Parameters.EnumParameter.MakeChild(enum_t=DopingType)
    operation_region = F.Parameters.EnumParameter.MakeChild(enum_t=OperationRegion)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    emitter.add_dependant(fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [emitter]))
    base.add_dependant(fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [base]))
    collector.add_dependant(
        fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [collector])
    )

    _can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeEdge(["collector"], ["emitter"])
    )

    _pin_association_heuristic = fabll.Traits.MakeEdge(
        F.has_pin_association_heuristic.MakeChild(
            mapping={
                emitter: ["E", "Emitter"],
                base: ["B", "Base"],
                collector: ["C", "Collector"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.Q)
    )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
    )
