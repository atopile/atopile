# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import StrEnum

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class Capacitor(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    # Updated to match the backend enum format
    class TemperatureCoefficient(StrEnum):
        Y5V = "1"
        Z5U = "2"
        X7S = "3"
        X5R = "4"
        X6R = "5"
        X7R = "6"
        X8R = "7"
        C0G = "8"

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    unnamed = [F.Electrical.MakeChild() for _ in range(2)]

    capacitance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Farad.MakeChild()
    )
    max_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt.MakeChild())
    temperature_coefficient = F.Parameters.EnumParameter.MakeChild(
        enum_t=TemperatureCoefficient
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
        F.is_pickable_by_type.MakeChild(
            endpoint=F.is_pickable_by_type.Endpoint.CAPACITORS,
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

    usage_example = F.has_usage_example.MakeChild(
        """
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
        F.has_usage_example.Language.ato,
    ).put_on_type()
