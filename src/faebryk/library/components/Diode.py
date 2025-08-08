# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from deprecated import deprecated

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import ParameterOperatable
from faebryk.libs.library import L
from faebryk.libs.units import P
from enum import Enum, StrEnum, auto


class Diode(Module):
    class DiodeType(StrEnum):
        PN = auto()
        SCHOTTKEY = auto()
        TVS = auto()
        ZENER = auto()
        RECTIFIER = auto()

    rated_forward_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.V, 1 * P.V),
        tolerance_guess=10 * P.percent,
    )
    """
    The maximumrated forward voltage drop at the rated forward current.
    """

    rated_forward_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.mA, 10 * P.A),
    )
    """
    Rated continuous forward current.
    """

    rated_reverse_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.mA, 10 * P.A),
    )
    """
    Rated continuous reverse current.
    """

    rated_reverse_blocking_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(10 * P.V, 100 * P.V),
        tolerance_guess=10 * P.percent,
    )
    """
    Rated reverse blocking voltage.
    """

    reverse_leakage_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.nA, 1 * P.µA),
        tolerance_guess=10 * P.percent,
    )
    """
    Reverse leakage current.
    """

    rated_power_dissipation = L.p_field(
        units=P.W,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.mW, 10 * P.W),
        tolerance_guess=10 * P.percent,
    )
    """
    Rated power dissipation.
    """

    @deprecated(reason="Use PoweredLED instead")
    forward_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.V, 1 * P.V),
        tolerance_guess=10 * P.percent,
    )
    current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.mA, 10 * P.A),
        tolerance_guess=10 * P.percent,
    )
    reverse_working_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(10 * P.V, 100 * P.V),
        tolerance_guess=10 * P.percent,
    )
    reverse_leakage_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.nA, 1 * P.µA),
        tolerance_guess=10 * P.percent,
    )
    max_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.mA, 10 * P.A),
    )

    anode: F.Electrical
    cathode: F.Electrical

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.DIODES,
            params=[self.rated_forward_voltage, self.rated_forward_current, self.rated_reverse_current, self.rated_reverse_blocking_voltage, self.reverse_leakage_current, self.rated_power_dissipation],
        )

    def __init__(self, diode_type: DiodeType = DiodeType.PN):
        super().__init__()
        self.diode_type = diode_type

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.anode, self.cathode)

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.D
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.anode: ["A", "Anode", "+"],
                self.cathode: ["K", "C", "Cathode", "-"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Diode, Resistor, ElectricPower

        diode = new Diode
        diode.forward_voltage = 0.7V +/- 10%
        diode.current = 10mA +/- 5%
        diode.reverse_working_voltage = 50V
        diode.max_current = 100mA
        diode.package = "SOD-123"

        # Connect as rectifier
        ac_input ~ diode.anode
        diode.cathode ~ dc_output

        # With current limiting resistor
        power_supply.hv ~> current_limit_resistor ~> diode ~> power_supply.lv
        """,
        language=F.has_usage_example.Language.ato,
    )

    class Package(StrEnum):
        _01005 = "PACKAGE"

    package = L.p_field(domain=L.Domains.ENUM(Package))
