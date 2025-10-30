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

    # ----------------------------------------
    #               parameters
    # ----------------------------------------
    frequency = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Hertz,
    )

    frequency_tolerance = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Ppm,
    )

    frequency_temperature_tolerance = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Ppm,
    )

    frequency_ageing = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Ppm,
    )

    equivalent_series_resistance = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Ohm,
    )

    shunt_capacitance = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Farad,
    )

    load_capacitance = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Farad,
    )

    # ----------------------------------------
    #                traits
    # ----------------------------------------
    footprint = F.can_attach_to_footprint_symmetrically.MakeChild()
    designator = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.XTAL
    ).put_on_type()

    usage_example = F.has_usage_example.MakeChild(
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
