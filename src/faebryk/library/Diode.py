# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import ParameterOperatable
from faebryk.libs.library import L
from faebryk.libs.units import P


class Diode(Module):
    forward_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.V, 1 * P.V),
        tolerance_guess=10 * P.percent,
    )
    # Current at which the design is functional
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
    # Current at which the design may be damaged
    # In some cases, this is useful to know, e.g. to calculate the brightness of an LED
    max_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.mA, 10 * P.A),
    )

    anode: F.Electrical
    cathode: F.Electrical

    pickable = L.f_field(F.is_pickable_by_type)(F.is_pickable_by_type.Type.Diode)

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.anode, self.cathode)

    @L.rt_field
    def simple_value_representation(self):
        S = F.has_simple_value_representation_based_on_params_chain.Spec
        return F.has_simple_value_representation_based_on_params_chain(
            S(self.forward_voltage),
        )

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

    def __preinit__(self):
        self.current.constrain_le(self.max_current)

    def get_needed_series_resistance_for_current_limit(
        self, input_voltage_V: ParameterOperatable
    ):
        return (input_voltage_V - self.forward_voltage) / self.current
