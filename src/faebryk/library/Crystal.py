# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class Crystal(Module):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    gnd: F.Electrical
    unnamed = L.list_field(2, F.Electrical)

    # ----------------------------------------
    #               parameters
    # ----------------------------------------
    frequency = L.p_field(
        units=P.Hz,
        likely_constrained=True,
        soft_set=L.Range(32.768 * P.kHz, 100 * P.MHz),
        tolerance_guess=50 * P.ppm,
    )

    frequency_tolerance = L.p_field(
        units=P.ppm,
        likely_constrained=True,
        soft_set=L.Range(10 * P.ppm, 100 * P.ppm),
        tolerance_guess=10 * P.percent,
    )

    frequency_temperature_tolerance = L.p_field(
        units=P.ppm,
        likely_constrained=True,
        soft_set=L.Range(1 * P.ppm, 50 * P.ppm),
        tolerance_guess=10 * P.percent,
    )

    frequency_ageing = L.p_field(
        units=P.ppm,
        likely_constrained=True,
        soft_set=L.Range(1 * P.ppm, 10 * P.ppm),
        tolerance_guess=20 * P.percent,
    )

    equivalent_series_resistance = L.p_field(
        units=P.Ω,
        likely_constrained=True,
        soft_set=L.Range(10 * P.Ω, 200 * P.Ω),
        tolerance_guess=10 * P.percent,
    )

    shunt_capacitance = L.p_field(
        units=P.F,
        likely_constrained=True,
        soft_set=L.Range(1 * P.pF, 10 * P.pF),
        tolerance_guess=20 * P.percent,
    )

    load_capacitance = L.p_field(
        units=P.F,
        likely_constrained=True,
        soft_set=L.Range(8 * P.pF, 30 * P.pF),
        tolerance_guess=10 * P.percent,
    )

    # ----------------------------------------
    #                traits
    # ----------------------------------------
    designator = L.f_field(F.has_designator_prefix)(F.has_designator_prefix.Prefix.XTAL)
    footprint: F.can_attach_to_footprint_symmetrically

    # ----------------------------------------
    #                connections
    # ----------------------------------------

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        #pragma experiment("BRIDGE_CONNECT")
        import Crystal, Capacitor, ElectricPower, Electrical

        module UsageExample:
            crystal = new Crystal
            crystal.lcsc_id = "C9002"
            # crystal.frequency = 12MHz +/- 20ppm
            # crystal.frequency_tolerance = 20ppm
            # crystal.load_capacitance = 20pF +/- 10%

            # Connect to microcontroller with load capacitors
            load_cap1 = new Capacitor
            load_cap2 = new Capacitor
            load_cap1.capacitance = 22pF +/- 5%
            load_cap2.capacitance = 22pF +/- 5%

            # Example MCU connections
            xtal1_pin = new Electrical
            xtal2_pin = new Electrical
            power_supply = new ElectricPower

            xtal1_pin ~ crystal.unnamed[0]
            xtal2_pin ~ crystal.unnamed[1]
            crystal.unnamed[0] ~> load_cap1 ~> crystal.gnd
            crystal.unnamed[1] ~> load_cap2 ~> crystal.gnd
            crystal.gnd ~ power_supply.lv
        """,
        language=F.has_usage_example.Language.ato,
    )
