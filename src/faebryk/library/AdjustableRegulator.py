# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F


class AdjustableRegulator(fabll.Node):
    """
    Adjustable regulator with resistor divider feedback.

    The feedback divider compares output voltage against a reference voltage
    to regulate the output.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # External interfaces
    power_in = F.ElectricPower.MakeChild()
    """Input power interface"""

    power_out = F.ElectricPower.MakeChild()
    """Regulated output power interface"""

    # Parameters
    input_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    """Voltage of power_in"""

    output_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    """Voltage of power_out"""

    reference_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    """Reference voltage of the regulator IC"""

    # dropout_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    # """Dropout voltage of the regulator (input - output minimum difference)"""

    # Components
    feedback_divider = F.ResistorVoltageDivider.MakeChild()
    """
    Resistor divider from output voltage used as feedback signal
    to be compared against reference voltage.

    To manage current draw of divider, constrain current or total_resistance.
    """

    # Mark as bridgeable between power_in and power_out
    _can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeChild(["power_in"], ["power_out"])
    )

    # Backwards compatibility aliases - v_in and v_out are aliases
    # to power_in.voltage and power_out.voltage respectively
    v_in = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    v_out = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)

    _connections = [
        # feedback_divider.ref_in ~ power_out
        fabll.is_interface.MakeConnectionEdge(
            [feedback_divider, F.ResistorVoltageDivider.ref_in], [power_out]
        ),
    ]

    # Parameter linkages and constraints
    _constraints = [
        # Link input_voltage/output_voltage to power interface voltages
        F.Expressions.Is.MakeChild(
            [input_voltage],
            [power_in, F.ElectricPower.voltage],
            assert_=True,
        ),
        F.Expressions.Is.MakeChild(
            [output_voltage],
            [power_out, F.ElectricPower.voltage],
            assert_=True,
        ),
        # v_in/v_out are aliases for input_voltage/output_voltage
        F.Expressions.Is.MakeChild(
            [v_in],
            [input_voltage],
            assert_=True,
        ),
        F.Expressions.Is.MakeChild(
            [v_out],
            [output_voltage],
            assert_=True,
        ),
        # Feedback divider constraints:
        # Link divider v_in to output_voltage (divider measures output)
        F.Expressions.Is.MakeChild(
            [feedback_divider, F.ResistorVoltageDivider.v_in],
            [output_voltage],
            assert_=True,
        ),
        # Link divider v_out to reference_voltage
        F.Expressions.Is.MakeChild(
            [feedback_divider, F.ResistorVoltageDivider.v_out],
            [reference_voltage],
            assert_=True,
        ),
        # Constrain divider current draw
        F.Literals.Numbers.MakeChild_SetSuperset(
            [feedback_divider, F.ResistorVoltageDivider.current],
            1e-6,
            1e-3,
            unit=F.Units.Ampere,
        ),
    ]
