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

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import OpAmp, Resistor, ElectricPower, Electrical

        opamp = new OpAmp
        opamp.bandwidth = 1MHz +/- 10%
        opamp.gain_bandwidth_product = 10MHz +/- 20%
        opamp.input_offset_voltage = 1mV +/- 50%
        opamp.slew_rate = 1V/us +/- 20%
        opamp.package = "SOIC-8"

        # Power supply connections (dual supply)
        power_pos = new ElectricPower
        power_neg = new ElectricPower
        assert power_pos.voltage within 5V +/- 5%
        assert power_neg.voltage within -5V +/- 5%
        opamp.power.hv ~ power_pos.hv
        opamp.power.lv ~ power_neg.lv

        # Non-inverting amplifier configuration
        feedback_resistor = new Resistor
        gain_resistor = new Resistor
        feedback_resistor.resistance = 10kohm +/- 1%
        gain_resistor.resistance = 1kohm +/- 1%

        # Connections for gain = 1 + (Rf/Rg) = 11
        input_signal ~ opamp.non_inverting_input
        opamp.inverting_input ~> gain_resistor ~> power_neg.lv
        opamp.output ~> feedback_resistor ~> opamp.inverting_input
        output_signal ~ opamp.output
        """,
        language=F.has_usage_example.Language.ato,
    )
