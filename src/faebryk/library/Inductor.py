# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F


class Inductor(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    unnamed = [F.Electrical.MakeChild() for _ in range(2)]

    inductance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Henry)
    max_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    dc_resistance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)
    saturation_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    self_resonant_frequency = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Hertz
    )

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _is_pickable = fabll.Traits.MakeEdge(
        F.is_pickable_by_type.MakeChild(
            endpoint=F.is_pickable_by_type.Endpoint.INDUCTORS,
            params={
                "inductance": inductance,
                "max_current": max_current,
                "dc_resistance": dc_resistance,
                "saturation_current": saturation_current,
                "self_resonant_frequency": self_resonant_frequency,
            },
        )
    )

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
        F.can_bridge.MakeChild(in_=unnamed[0], out_=unnamed[1])
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.L)
    )

    S = F.has_simple_value_representation.Spec
    _simple_repr = fabll.Traits.MakeEdge(
        F.has_simple_value_representation.MakeChild(
            S(inductance, tolerance=True, prefix="L"),
            S(self_resonant_frequency, prefix="SRF"),
            S(max_current, prefix="Imax"),
            S(dc_resistance, prefix="DCR"),
        )
    )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
        ).put_on_type()
    )
