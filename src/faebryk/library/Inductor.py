# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P


class Inductor(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    unnamed = [F.Electrical.MakeChild() for _ in range(2)]

    inductance = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Henry)
    max_current = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Ampere)
    dc_resistance = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Ohm)
    saturation_current = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Ampere)
    self_resonant_frequency = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Hertz)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.is_module.MakeChild()

    _is_pickable = F.is_pickable_by_type.MakeChild(
        endpoint=F.is_pickable_by_type.Endpoint.INDUCTORS,
        params={
            "inductance": inductance,
            "max_current": max_current,
            "dc_resistance": dc_resistance,
            "saturation_current": saturation_current,
            "self_resonant_frequency": self_resonant_frequency,
        },
    )

    _can_attach = F.can_attach_to_footprint_symmetrically.MakeChild()
    _can_bridge = F.can_bridge.MakeChild(in_=unnamed[0], out_=unnamed[1])

    S = F.has_simple_value_representation.Spec
    _simple_repr = F.has_simple_value_representation.MakeChild(
        S(inductance, tolerance=True),
        S(self_resonant_frequency),
        S(max_current),
        S(dc_resistance),
    )

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.L
    )

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import Inductor

        inductor = new Inductor
        inductor.inductance = 10uH +/- 10%
        inductor.max_current = 2A
        inductor.dc_resistance = 50mohm +/- 20%
        inductor.self_resonant_frequency = 100MHz +/- 10%
        inductor.package = "0805"

        electrical1 ~ inductor.unnamed[0]
        electrical2 ~ inductor.unnamed[1]
        # OR
        electrical1 ~> inductor ~> electrical2

        # For filtering applications
        power_input ~> inductor ~> filtered_output
        """,
        language=F.has_usage_example.Language.ato,
    )
