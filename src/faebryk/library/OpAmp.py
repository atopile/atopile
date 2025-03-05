# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class OpAmp(Module):
    bandwidth = L.p_field(units=P.Hz)
    common_mode_rejection_ratio = L.p_field(units=P.dB)
    input_bias_current = L.p_field(units=P.A)
    input_offset_voltage = L.p_field(units=P.V)
    gain_bandwidth_product = L.p_field(units=P.Hz)
    output_current = L.p_field(units=P.A)
    slew_rate = L.p_field(units=P.V / P.s)

    power: F.ElectricPower
    inverting_input: F.Electrical
    non_inverting_input: F.Electrical
    output: F.Electrical

    @L.rt_field
    def simple_value_representation(self):
        S = F.has_simple_value_representation_based_on_params_chain.Spec
        return F.has_simple_value_representation_based_on_params_chain(
            S(self.bandwidth, suffix="BW"),
            S(self.common_mode_rejection_ratio, suffix="CMRR"),
            S(self.input_bias_current, suffix="Ib"),
            S(self.input_offset_voltage, suffix="Vos"),
            S(self.gain_bandwidth_product, suffix="GBW"),
            S(self.output_current, suffix="Iout"),
            S(self.slew_rate, suffix="SR"),
        )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power.hv: ["V+", "Vcc", "Vdd", "Vcc+"],
                self.power.lv: ["V-", "Vee", "Vss", "GND", "Vcc-"],
                self.inverting_input: ["-", "IN-"],
                self.non_inverting_input: ["+", "IN+"],
                self.output: ["OUT"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @property
    def inverting(self) -> F.Electrical:
        return self.inverting_input

    @property
    def non_inverting(self) -> F.Electrical:
        return self.non_inverting_input
