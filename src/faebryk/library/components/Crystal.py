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
    rated_frequency = L.p_field(
        units=P.Hz,
        likely_constrained=True,
        soft_set=L.Range(32.768 * P.kHz, 100 * P.MHz),
        tolerance_guess=50 * P.ppm,
    )

    rated_frequency_tolerance = L.p_field(
        units=P.ppm,
        likely_constrained=True,
        soft_set=L.Range(10 * P.ppm, 100 * P.ppm),
        tolerance_guess=10 * P.percent,
    )

    rated_frequency_temperature_tolerance = L.p_field(
        units=P.ppm,
        likely_constrained=True,
        soft_set=L.Range(1 * P.ppm, 50 * P.ppm),
        tolerance_guess=10 * P.percent,
    )

    rated_frequency_ageing = L.p_field(
        units=P.ppm,
        likely_constrained=True,
        soft_set=L.Range(1 * P.ppm, 10 * P.ppm),
        tolerance_guess=20 * P.percent,
    )

    rated_equivalent_series_resistance = L.p_field(
        units=P.Ω,
        likely_constrained=True,
        soft_set=L.Range(10 * P.Ω, 200 * P.Ω),
        tolerance_guess=10 * P.percent,
    )

    rated_shunt_capacitance = L.p_field(
        units=P.F,
        likely_constrained=True,
        soft_set=L.Range(1 * P.pF, 10 * P.pF),
        tolerance_guess=20 * P.percent,
    )

    rated_load_capacitance = L.p_field(
        units=P.F,
        likely_constrained=True,
        soft_set=L.Range(8 * P.pF, 30 * P.pF),
        tolerance_guess=10 * P.percent,
    )

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.CRYSTALS,
            params=[
                self.rated_frequency,
                self.rated_frequency_tolerance,
                self.rated_frequency_temperature_tolerance,
                self.rated_frequency_ageing,
                self.rated_equivalent_series_resistance,
                self.rated_shunt_capacitance,
                self.rated_load_capacitance,
            ],
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
    )

    class Package(StrEnum):
        _01005 = auto()

    package = L.p_field(domain=L.Domains.ENUM(Package))
