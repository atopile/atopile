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
        [power, "hv"],
        [r_top, "unnamed[0]"],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # r_top.unnamed[1] ~ output.line
    _conn_rtop_to_output = fabll.MakeEdge(
        [r_top, "unnamed[1]"],
        [output, "line"],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # output.line ~ r_bottom.unnamed[0]
    _conn_output_to_rbottom = fabll.MakeEdge(
        [output, "line"],
        [r_bottom, "unnamed[0]"],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # r_bottom.unnamed[1] ~ power.lv
    _conn_rbottom_to_lv = fabll.MakeEdge(
        [r_bottom, "unnamed[1]"],
        [power, "lv"],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # Connect output signal reference to power (ground reference)
    _conn_output_ref = fabll.MakeEdge(
        [output, "reference"],
        [power],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # ----------------------------------------
    #            Expressions
    # ----------------------------------------
    # Link interface voltages to parameters
    # v_out IS output.reference.voltage
    _eq_v_out_voltage = F.Expressions.Is.MakeChild(
        [v_out], [output, "reference", "voltage"], assert_=True
    )
    # v_in IS power.voltage
    _eq_v_in_voltage = F.Expressions.Is.MakeChild(
        [v_in], [power, "voltage"], assert_=True
    )

    # r_total IS r_top + r_bottom
    _add_r_total = F.Expressions.Add.MakeChild(
        [r_top, "resistance"], [r_bottom, "resistance"]
    )
    _eq_r_total = F.Expressions.Is.MakeChild(
        [total_resistance], [_add_r_total], assert_=True
    )

    # ratio IS r_bottom / r_total
    _div_ratio = F.Expressions.Divide.MakeChild(
        [r_bottom, "resistance"], [total_resistance]
    )
    _eq_ratio = F.Expressions.Is.MakeChild([ratio], [_div_ratio], assert_=True)

    # r_bottom IS r_total * ratio
    _mul_r_bottom = F.Expressions.Multiply.MakeChild([total_resistance], [ratio])
    _eq_r_bottom_from_ratio = F.Expressions.Is.MakeChild(
        [r_bottom, "resistance"], [_mul_r_bottom], assert_=True
    )

    # Literal 1 for equations
    _lit_one = F.Literals.Numbers.MakeChild_SingleValue(
        value=1.0, unit=F.Units.Dimensionless
    )

    # r_top IS r_total * (1 - ratio)
    _sub_one_minus_ratio = F.Expressions.Subtract.MakeChild([_lit_one], [ratio])
    _mul_r_top_from_ratio = F.Expressions.Multiply.MakeChild(
        [total_resistance], [_sub_one_minus_ratio]
    )
    _eq_r_top_from_ratio = F.Expressions.Is.MakeChild(
        [r_top, "resistance"], [_mul_r_top_from_ratio], assert_=True
    )

    # v_out IS v_in * ratio
    _mul_v_out = F.Expressions.Multiply.MakeChild([v_in], [ratio])
    _eq_v_out_from_ratio = F.Expressions.Is.MakeChild(
        [v_out], [_mul_v_out], assert_=True
    )

    # v_out IS v_in * r_bottom / r_total
    _mul_v_in_r_bottom = F.Expressions.Multiply.MakeChild(
        [v_in], [r_bottom, "resistance"]
    )
    _div_v_out = F.Expressions.Divide.MakeChild(
        [_mul_v_in_r_bottom], [total_resistance]
    )
    _eq_v_out_from_resistors = F.Expressions.Is.MakeChild(
        [v_out], [_div_v_out], assert_=True
    )

    # ratio IS v_out / v_in
    _div_ratio_from_v = F.Expressions.Divide.MakeChild([v_out], [v_in])
    _eq_ratio_from_v = F.Expressions.Is.MakeChild(
        [ratio], [_div_ratio_from_v], assert_=True
    )

    # max_current IS v_in / r_total
    _div_max_current = F.Expressions.Divide.MakeChild([v_in], [total_resistance])
    _eq_max_current = F.Expressions.Is.MakeChild(
        [max_current], [_div_max_current], assert_=True
    )

    # r_total IS v_in / max_current
    _div_r_total_from_i = F.Expressions.Divide.MakeChild([v_in], [max_current])
    _eq_r_total_from_i = F.Expressions.Is.MakeChild(
        [total_resistance], [_div_r_total_from_i], assert_=True
    )

    # r_top IS (v_in - v_out) / max_current
    _sub_v_diff = F.Expressions.Subtract.MakeChild([v_in], [v_out])
    _div_r_top_from_i = F.Expressions.Divide.MakeChild([_sub_v_diff], [max_current])
    _eq_r_top_from_i = F.Expressions.Is.MakeChild(
        [r_top, "resistance"], [_div_r_top_from_i], assert_=True
    )

    # r_bottom IS v_out / max_current
    _div_r_bottom_from_i = F.Expressions.Divide.MakeChild([v_out], [max_current])
    _eq_r_bottom_from_i = F.Expressions.Is.MakeChild(
        [r_bottom, "resistance"], [_div_r_bottom_from_i], assert_=True
    )

    # r_bottom IS v_out * r_top / (v_in - v_out)
    _mul_v_out_r_top = F.Expressions.Multiply.MakeChild([v_out], [r_top, "resistance"])
    _sub_v_in_v_out = F.Expressions.Subtract.MakeChild([v_in], [v_out])
    _div_r_bottom_cross = F.Expressions.Divide.MakeChild(
        [_mul_v_out_r_top], [_sub_v_in_v_out]
    )
    _eq_r_bottom_cross = F.Expressions.Is.MakeChild(
        [r_bottom, "resistance"], [_div_r_bottom_cross], assert_=True
    )

    # r_top IS r_bottom * (v_in / v_out - 1)
    _div_v_ratio = F.Expressions.Divide.MakeChild([v_in], [v_out])
    _sub_v_ratio_minus_1 = F.Expressions.Subtract.MakeChild([_div_v_ratio], [_lit_one])
    _mul_r_top_cross = F.Expressions.Multiply.MakeChild(
        [r_bottom, "resistance"], [_sub_v_ratio_minus_1]
    )
    _eq_r_top_cross = F.Expressions.Is.MakeChild(
        [r_top, "resistance"], [_mul_r_top_cross], assert_=True
    )

    output.add_dependant(
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="VDIV_OUTPUT", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            [output, "line"],
        )
    )
