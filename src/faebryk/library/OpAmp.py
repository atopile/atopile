# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class OpAmp(Module):
    bandwidth: F.TBD
    common_mode_rejection_ratio: F.TBD
    input_bias_current: F.TBD
    input_offset_voltage: F.TBD
    gain_bandwidth_product: F.TBD
    output_current: F.TBD
    slew_rate: F.TBD

    power: F.ElectricPower
    inverting_input: F.Electrical
    non_inverting_input: F.Electrical
    output: F.Electrical

    @L.rt_field
    def simple_value_representation(self):
        return F.has_simple_value_representation_based_on_params(
            (
                self.bandwidth,
                self.common_mode_rejection_ratio,
                self.input_bias_current,
                self.input_offset_voltage,
                self.gain_bandwidth_product,
                self.output_current,
                self.slew_rate,
            ),
            lambda bandwidth,
            common_mode_rejection_ratio,
            input_bias_current,
            input_offset_voltage,
            gain_bandwidth_product,
            output_current,
            slew_rate: ", ".join(
                [
                    f"{bandwidth.as_unit("Hz")} BW",
                    f"{common_mode_rejection_ratio} CMRR",
                    f"{input_bias_current.as_unit("A")} Ib",
                    f"{input_offset_voltage.as_unit("V")} Vos",
                    f"{gain_bandwidth_product.as_unit("Hz")} GBW",
                    f"{output_current.as_unit("A")} Iout",
                    f"{slew_rate.as_unit("V/s")} SR",
                ]
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

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )
