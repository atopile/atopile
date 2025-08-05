# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class Resistor(Module):
    unnamed = L.list_field(2, F.Electrical)

    resistance = L.p_field(units=P.ohm)
    max_power = L.p_field(units=P.W)
    max_voltage = L.p_field(units=P.V)

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.R
    )

    @L.rt_field
    def pickable(self) -> F.is_pickable_by_type:
        return F.is_pickable_by_type(
            F.is_pickable_by_type.Type.Resistor,
            {
                "resistance": self.resistance,
                "max_power": self.max_power,
                "max_voltage": self.max_voltage,
            },
        )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.unnamed)

    @L.rt_field
    def simple_value_representation(self):
        S = F.has_simple_value_representation_based_on_params_chain.Spec
        return F.has_simple_value_representation_based_on_params_chain(
            S(self.resistance, tolerance=True),
            S(self.max_power),
        )

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

            electrical1 ~ resistor.unnamed[0]
            electrical2 ~ resistor.unnamed[1]
            # OR
            electrical1 ~> resistor ~> electrical2
        """,
        language=F.has_usage_example.Language.ato,
    )
