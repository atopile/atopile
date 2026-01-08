# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import IntEnum, auto

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class Capacitor(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    class TemperatureCoefficient(IntEnum):
        Y5V = auto()
        Z5U = auto()
        X7S = auto()
        X5R = auto()
        X6R = auto()
        X7R = auto()
        X8R = auto()
        C0G = auto()

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    unnamed = [F.Electrical.MakeChild() for _ in range(2)]

    capacitance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Farad)
    max_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    temperature_coefficient = F.Parameters.EnumParameter.MakeChild(
        enum_t=TemperatureCoefficient
    )

    # Alias for backwards compatibility
    power = F.ElectricPower.MakeChild()
    # Connect power to unnamed[0] and unnamed[1]
    _ = fabll.MakeEdge(
        [power, "hv"],
        [unnamed[0]],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )
    _ = fabll.MakeEdge(
        [power, "lv"],
        [unnamed[1]],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    for e in unnamed:
        lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [e])
        lead.add_dependant(
            fabll.Traits.MakeEdge(F.Lead.can_attach_to_any_pad.MakeChild(), [lead])
        )
        e.add_dependant(lead)

    _can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeEdge(["unnamed[0]"], ["unnamed[1]"])
    )

    _is_pickable = fabll.Traits.MakeEdge(
        F.Pickable.is_pickable_by_type.MakeChild(
            endpoint=F.Pickable.is_pickable_by_type.Endpoint.CAPACITORS,
            params={
                "capacitance": capacitance,
                "max_voltage": max_voltage,
                "temperature_coefficient": temperature_coefficient,
            },
        )
    )

    S = F.has_simple_value_representation.Spec
    _simple_repr = fabll.Traits.MakeEdge(
        F.has_simple_value_representation.MakeChild(
            S(capacitance),  # first spec shows up as value field
            S(capacitance, tolerance=True),
            S(max_voltage),
            S(temperature_coefficient),
        )
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.C)
    )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
                import Capacitor

                capacitor = new Capacitor
                capacitor.capacitance = 100nF +/- 10%
                assert capacitor.max_voltage within 25V to 50V
                capacitor.package = "0603"

                electrical1 ~ capacitor.unnamed[0]
                electrical2 ~ capacitor.unnamed[1]
                # OR
                electrical1 ~> capacitor ~> electrical2
            """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
