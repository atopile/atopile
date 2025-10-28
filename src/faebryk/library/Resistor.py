# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class Resistor(fabll.Node):
    unnamed = [F.Electrical.MakeChild() for _ in range(2)]

    resistance = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Ohm)
    max_power = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Watt)
    max_voltage = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Volt)

    _can_attach = F.can_attach_to_footprint_symmetrically.MakeChild()
    _can_bridge = F.can_bridge.MakeChild(in_=unnamed[0], out_=unnamed[1])

    _is_pickable = F.is_pickable_by_type.MakeChild(
        endpoint="resistors",
        params={
            "resistance": resistance,
            "max_power": max_power,
            "max_voltage": max_voltage,
        },
    )

    _simple_repr = F.has_simple_value_representation_based_on_params_chain.MakeChild(
        params={
            "resistance": resistance,
            "max_power": max_power,
        }
    )

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.R
    ).put_on_type()

    usage_example = F.has_usage_example.MakeChild(
        """
            import Resistor
            resistor = new Resistor
            resistor.resistance = 10kohm +/- 5%
        """,
        F.has_usage_example.Language.ato,
    ).put_on_type()
