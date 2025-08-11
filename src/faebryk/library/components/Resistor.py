# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class Resistor(Module):
    """
    A resistor is a passive two-terminal electrical component. Resistors can be
    configured by specifying a range for the following parameters:
    - resistance: The resistance of the resistor in ohms.
    - max_power: The maximum rated power that the resistor can dissipate in watts.
    - max_voltage: The maximum rated voltage that the resistor can withstand in volts.
    - package: The imperial SMD package of the resistor.
    """

    # TODO: Deprecated unnamed -> terminals
    terminals = L.list_field(2, F.Electrical)

    resistance = L.p_field(units=P.ohm)
    rated_power = L.p_field(units=P.W)
    rated_max_voltage = L.p_field(units=P.V)

    max_power = L.deprecated_field(message="Use rated_power instead")
    max_voltage = L.deprecated_field(message="Use rated_max_voltage instead")

    attach_to_footprint: F.can_attach_to_footprint_symmetrically

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.RESISTORS,
            params=[
                self.resistance,
                self.rated_power,
                self.rated_max_voltage,
                self.package,
            ],
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.R
    )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.terminals)

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        #pragma experiment("BRIDGE_CONNECT")

        import Electrical, Resistor

        module App:
            resistor = new Resistor
            resistor.resistance = 100ohm +/- 5%
            assert resistor.max_power >= 100mW
            assert resistor.max_voltage >= 10V
            resistor.package = "0402"

            electrical1 = new Electrical
            electrical2 = new Electrical

            electrical1 ~ resistor.terminals[0]
            electrical2 ~ resistor.terminals[1]
            # OR
            electrical1 ~> resistor ~> electrical2
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
