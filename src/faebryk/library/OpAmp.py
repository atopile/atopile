# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import Quantity


class OpAmp(Module):
    bandwidth: F.TBD[Quantity]
    common_mode_rejection_ratio: F.TBD[Quantity]
    input_bias_current: F.TBD[Quantity]
    input_offset_voltage: F.TBD[Quantity]
    gain_bandwidth_product: F.TBD[Quantity]
    output_current: F.TBD[Quantity]
    slew_rate: F.TBD[Quantity]

    power: F.ElectricPower
    inverting_input: F.Electrical
    non_inverting_input: F.Electrical
    output: F.Electrical

    @L.rt_field
    def simple_value_representation(self):
        from faebryk.core.util import as_unit

        return F.has_simple_value_representation_based_on_params(
            [
                self.bandwidth,
                self.common_mode_rejection_ratio,
                self.input_bias_current,
                self.input_offset_voltage,
                self.gain_bandwidth_product,
                self.output_current,
                self.slew_rate,
            ],
            lambda p: (
                f"{as_unit(p[0], 'Hz')} BW, {p[1]} CMRR, {as_unit(p[2], 'A')} Ib, "
                f"{as_unit(p[3], 'V')} Vos, {as_unit(p[4], 'Hz')} GBW, "
                f"{as_unit(p[5], 'A')} Iout, {as_unit(p[6], 'V/s')} SR"
            ),
        )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power.hv: ["V+", "Vcc", "Vdd"],
                self.power.lv: ["V-", "Vee", "Vss", "GND"],
                self.inverting_input: ["-", "IN-"],
                self.non_inverting_input: ["+", "IN+"],
                self.output: ["OUT"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("U")
