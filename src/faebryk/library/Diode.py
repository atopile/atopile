# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.libs.library import L


class Diode(Module):
    forward_voltage: F.TBD
    max_current: F.TBD
    current: F.TBD
    reverse_working_voltage: F.TBD
    reverse_leakage_current: F.TBD

    anode: F.Electrical
    cathode: F.Electrical

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.anode, self.cathode)

    @L.rt_field
    def simple_value_representation(self):
        return F.has_simple_value_representation_based_on_params(
            (self.forward_voltage,),
            lambda p: p.as_unit("V"),
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
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

    def get_needed_series_resistance_for_current_limit(
        self, input_voltage_V: Parameter
    ) -> Parameter:
        return (input_voltage_V - self.forward_voltage) / self.current
