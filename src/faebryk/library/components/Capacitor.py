# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, StrEnum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class Capacitor(Module):
    """
    A capacitor is a passive two-terminal electrical component. Capacitors can be configured by specifying a range for the following parameters:
    - capacitance: The capacitance of the capacitor in farads.
    - max_voltage: The maximum rated voltage that the capacitor can withstand in volts.
    - package: The imperial SMD package of the capacitor.
    """

    class TemperatureCoefficient(Enum):
        Y5V = auto()
        Z5U = auto()
        X7S = auto()
        X5R = auto()
        X6R = auto()
        X7R = auto()
        X8R = auto()
        C0G = auto()

    # TODO: Deprecated unnamed -> terminals
    terminals = L.list_field(2, F.Electrical)

    capacitance = L.p_field(
        units=P.F,
        likely_constrained=True,
        soft_set=L.Range(100 * P.pF, 1 * P.F),
        tolerance_guess=10 * P.percent,
    )
    # TODO: Deprecated max_voltage -> rated_voltage
    rated_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(10 * P.V, 100 * P.V),
    )
    temperature_coefficient = L.p_field(
        domain=L.Domains.ENUM(TemperatureCoefficient),
    )

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.CAPACITORS,
            params=[
                self.capacitance,
                self.rated_voltage,
                self.temperature_coefficient,
                self.package,
            ],
        )

    attach_to_footprint: F.can_attach_to_footprint_symmetrically

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.C
    )

    def can_bridge(self):
        return F.can_bridge_defined(*self.terminals)

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Electrcal, Capacitor

        capacitor = new Capacitor
        capacitor.capacitance = 100nF +/- 10%
        assert capacitor.max_voltage within 25V to 50V
        capacitor.package = "0603"

        electrical1 = new Electrical
        electrical2 = new Electrical

        electrical1 ~ capacitor.terminals[0]
        electrical2 ~ capacitor.terminals[1]
        # OR
        electrical1 ~> capacitor ~> electrical2
        """,
        language=F.has_usage_example.Language.ato,
    )

    class Package(StrEnum):
        _01005 = auto()
        _0201 = auto()
        _0402 = auto()
        _0603 = auto()
        _0805 = auto()
        _1206 = auto()
        _1210 = auto()
        _1808 = auto()
        _1812 = auto()
        _1825 = auto()
        _2220 = auto()
        _2225 = auto()
        _3640 = auto()

    package = L.p_field(domain=L.Domains.ENUM(Package))
