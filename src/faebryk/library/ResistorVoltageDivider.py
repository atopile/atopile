# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class ResistorVoltageDivider(fabll.Node):
    """
    A voltage divider using two resistors.
    node[0] ~ resistor[1] ~ node[1] ~ resistor[2] ~ node[2]
    power.hv ~ node[0]
    power.lv ~ node[2]
    output.line ~ node[1]
    output.reference.lv ~ node[2]
    """

    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # External interfaces
    power = F.ElectricPower.MakeChild()
    output = F.ElectricSignal.MakeChild()

    # Components
    r_bottom = F.Resistor.MakeChild()
    r_top = F.Resistor.MakeChild()

    # Variables
    v_in = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    v_out = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    max_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    total_resistance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)
    ratio = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    # ----------------------------------------
    #            Connections
    # ----------------------------------------
    # Topology: power.hv ~ r_top ~ output.line ~ r_bottom ~ power.lv

    # power.hv ~ r_top.unnamed[0]
    _conn_hv_to_rtop = fabll.MakeEdge(
        [power, F.ElectricPower.hv],
        [r_top, F.Resistor.unnamed[0]],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # r_top.unnamed[1] ~ output.line
    _conn_rtop_to_output = fabll.MakeEdge(
        [r_top, F.Resistor.unnamed[1]],
        [output, F.ElectricSignal.line],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # output.line ~ r_bottom.unnamed[0]
    _conn_output_to_rbottom = fabll.MakeEdge(
        [output, F.ElectricSignal.line],
        [r_bottom, F.Resistor.unnamed[0]],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # r_bottom.unnamed[1] ~ power.lv
    _conn_rbottom_to_lv = fabll.MakeEdge(
        [r_bottom, F.Resistor.unnamed[1]],
        [power, F.ElectricPower.lv],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # Connect output signal reference to power (ground reference)
    _conn_output_ref = fabll.MakeEdge(
        [output, F.ElectricSignal.reference],
        [power],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # ----------------------------------------
    #            Expressions
    # ----------------------------------------
    # Link interface voltages to parameters
    # v_out is! output.reference.voltage
    _eq_v_out_voltage = F.Expressions.Is.MakeChild(
        [v_out],
        [output, F.ElectricSignal.reference, F.ElectricPower.voltage],
        assert_=True,
    )
    # v_in is! power.voltage
    _eq_v_in_voltage = F.Expressions.Is.MakeChild(
        [v_in],
        [power, F.ElectricPower.voltage],
        assert_=True,
    )

    # r_total is! r_top + r_bottom
    _eq_r_total_add = F.Expressions.Add.MakeChild(
        [r_top, F.Resistor.resistance],
        [r_bottom, F.Resistor.resistance],
    )
    _eq_r_total = F.Expressions.Is.MakeChild(
        [total_resistance],
        [_eq_r_total_add],
        assert_=True,
    )

    # ratio is! r_bottom / r_total
    _eq_ratio_divide = F.Expressions.Divide.MakeChild(
        [r_bottom, F.Resistor.resistance], [total_resistance]
    )
    _eq_ratio = F.Expressions.Is.MakeChild(
        [ratio],
        [_eq_ratio_divide],
        assert_=True,
    )

    # ratio is! v_out / v_in
    _eq_ratio_from_v_divide = F.Expressions.Divide.MakeChild([v_out], [v_in])
    _eq_ratio_from_v = F.Expressions.Is.MakeChild(
        [ratio],
        [_eq_ratio_from_v_divide],
        assert_=True,
    )

    # max_current is! v_in / r_total
    _eq_max_current_divide = F.Expressions.Divide.MakeChild([v_in], [total_resistance])
    _eq_max_current = F.Expressions.Is.MakeChild(
        [max_current],
        [_eq_max_current_divide],
        assert_=True,
    )

    _net_name = fabll.Traits.MakeEdge(
        F.has_net_name_suggestion.MakeChild(
            name="VDIV_OUTPUT", level=F.has_net_name_suggestion.Level.SUGGESTED
        ),
        [output, "line"],
    )
