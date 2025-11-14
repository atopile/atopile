# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class OpAmp(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power = F.ElectricPower.MakeChild()
    input = F.DifferentialPair.MakeChild()
    output = F.Electrical.MakeChild()

    bandwidth = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Hertz)
    common_mode_rejection_ratio = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Decibel
    )
    input_bias_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    input_offset_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    gain_bandwidth_product = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Hertz)
    output_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    slew_rate = F.Parameters.NumericParameter.MakeChild(unit=F.Units.VoltsPerSecond)

    S = F.has_simple_value_representation.Spec
    _simple_repr = fabll.Traits.MakeEdge(
        F.has_simple_value_representation.MakeChild(
            S(bandwidth, prefix="BW"),
            S(common_mode_rejection_ratio, prefix="CMRR"),
            S(input_bias_current, prefix="Ib"),
            S(input_offset_voltage, prefix="Vos"),
            S(gain_bandwidth_product, prefix="GBW"),
            S(output_current, prefix="Iout"),
            S(slew_rate, prefix="SR"),
        )
    )

    _pin_association_heuristic = fabll.Traits.MakeEdge(
        F.has_pin_association_heuristic.MakeChild(
            mapping={
                # power.get().hv: ["V+", "Vcc", "Vdd", "Vcc+"], not possible for now
                # power.get().lv: ["V-", "Vee", "Vss", "GND", "Vcc-"],
                # input.get().n: ["-", "IN-"],
                # input.get().p: ["+", "IN+"],
                output: ["OUT"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.U)
    )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
    )
