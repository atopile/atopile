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
