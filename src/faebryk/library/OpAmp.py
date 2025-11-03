# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P


class OpAmp(fabll.Node):
    bandwidth = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Hertz)
    common_mode_rejection_ratio = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Decibel
    )
    input_bias_current = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Ampere)
    input_offset_voltage = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Volt)
    gain_bandwidth_product = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Hertz)
    output_current = fabll.Parameter.MakeChild_Numeric(unit=F.Units.Ampere)
    # slew_rate = fabll.Parameter.MakeChild_Numeric(
    #     unit=F.Units.Volt / F.Units.Second
    # )

    power = F.ElectricPower.MakeChild()
    inverting_input = F.Electrical.MakeChild()
    non_inverting_input = F.Electrical.MakeChild()
    output = F.Electrical.MakeChild()

    S = F.has_simple_value_representation_based_on_params_chain.Spec
    _simple_repr = F.has_simple_value_representation_based_on_params_chain.MakeChild(
        S(bandwidth, suffix="BW"),
        S(common_mode_rejection_ratio, suffix="CMRR"),
        S(input_bias_current, suffix="Ib"),
        S(input_offset_voltage, suffix="Vos"),
        S(gain_bandwidth_product, suffix="GBW"),
        S(output_current, suffix="Iout"),
        # S(slew_rate, suffix="SR"),
    )

    _pin_association_heuristic = F.has_pin_association_heuristic_lookup_table.MakeChild(
        mapping={
            power.nodetype.hv: ["V+", "Vcc", "Vdd", "Vcc+"],
            power.nodetype.lv: ["V-", "Vee", "Vss", "GND", "Vcc-"],
            inverting_input: ["-", "IN-"],
            non_inverting_input: ["+", "IN+"],
            output: ["OUT"],
        },
        accept_prefix=False,
        case_sensitive=False,
    )

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.U
    )

    @property
    def inverting(self) -> F.Electrical:
        return self.inverting_input.get()

    @property
    def non_inverting(self) -> F.Electrical:
        return self.non_inverting_input.get()

    usage_example = F.has_usage_example.MakeChild(
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
    ).put_on_type()
