# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class Crystal(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    gnd = F.Electrical.MakeChild()
    unnamed = [F.Electrical.MakeChild() for _ in range(2)]

    frequency = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Hertz,
    )

    frequency_tolerance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Ppm,
    )

    frequency_temperature_tolerance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Ppm,
    )

    frequency_ageing = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Ppm,
    )

    equivalent_series_resistance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Ohm,
    )

    shunt_capacitance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Farad,
    )

    load_capacitance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Farad,
    )

    # ----------------------------------------
    #                traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    gnd.add_dependant(fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [gnd]))

    for e in unnamed:
        lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [e])
        lead.add_dependant(
            fabll.Traits.MakeEdge(F.Lead.can_attach_to_any_pad.MakeChild(), [lead])
        )
        e.add_dependant(lead)

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.XTAL)
    )

    S = F.has_simple_value_representation.Spec
    _simple_repr = fabll.Traits.MakeEdge(
        F.has_simple_value_representation.MakeChild(
            S(frequency, tolerance=True),
        )
    )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        import Crystal, Capacitor

        crystal = new Crystal
        crystal.frequency = 16MHz +/- 20ppm
        crystal.frequency_tolerance = 20ppm
        crystal.load_capacitance = 18pF +/- 10%
        crystal.equivalent_series_resistance = 80ohm +/- 20%
        crystal.package = "HC49U"

        # Connect to microcontroller with load capacitors
        load_cap1 = new Capacitor
        load_cap2 = new Capacitor
        load_cap1.capacitance = 22pF +/- 5%
        load_cap2.capacitance = 22pF +/- 5%

        mcu.xtal1 ~ crystal.unnamed[0]
        mcu.xtal2 ~ crystal.unnamed[1]
        crystal.unnamed[0] ~> load_cap1 ~> crystal.gnd
        crystal.unnamed[1] ~> load_cap2 ~> crystal.gnd
        crystal.gnd ~ power_supply.lv
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
