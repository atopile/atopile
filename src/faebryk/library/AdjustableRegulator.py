# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.faebrykpy as fbrk
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

    To manage current draw of divider, constrain any one of:
    max_current, r_total, r_bottom, or r_top
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
        fabll.is_interface.MakeConnectionEdge(
            [v_in], [power_in, F.ElectricPower.voltage]
        ),
        fabll.is_interface.MakeConnectionEdge(
            [v_out], [power_out, F.ElectricPower.voltage]
        ),
    ]
