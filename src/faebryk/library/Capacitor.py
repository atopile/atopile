# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)

class Capacitor(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    class TemperatureCoefficient(Enum):
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
    capacitance = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Farad)
    max_voltage = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Volt)
    # temperature_coefficient = fabll.Parameter.MakeChild_Enum(
    #     enum_t=TemperatureCoefficient
    # )

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.is_module.MakeChild()
    _can_attach = F.can_attach_to_footprint_symmetrically.MakeChild()
    _can_bridge = F.can_bridge.MakeChild(in_=unnamed[0], out_=unnamed[1])
    _is_pickable = F.is_pickable_by_type.MakeChild(
        endpoint=F.is_pickable_by_type.Endpoint.CAPACITORS,
        params={
            "capacitance": capacitance,
            "max_voltage": max_voltage,
            # "temperature_coefficient": temperature_coefficient,
        },
    )

    S = F.has_simple_value_representation.Spec
    _simple_repr = F.has_simple_value_representation.MakeChild(
        S(capacitance, tolerance=True),
        S(max_voltage),
        # S(temperature_coefficient),
    )

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.C
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
    )
