# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class FilterElectricalRC(fabll.Node):
    """
    Basic Electrical RC filter (low-pass)

    Topology:
        in_.line ~> resistor ~> out.line
        out.line ~> capacitor ~> in_.reference.lv (ground)
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    in_ = F.ElectricSignal.MakeChild()
    out = F.ElectricSignal.MakeChild()
    resistor = F.Resistor.MakeChild()
    capacitor = F.Capacitor.MakeChild()

    filter = F.Filter.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    can_bridge = fabll.Traits.MakeEdge(F.can_bridge.MakeChild(["in_"], ["out"]))

    # ----------------------------------------
    #            Connections
    # ----------------------------------------
    # Topology: in_.line ~> resistor ~> out.line
    #           out.line ~> capacitor ~> in_.reference.lv

    # in_.line ~ resistor.unnamed[0]
    _conn_in_to_resistor = fabll.MakeEdge(
        [in_, "line"],
        [resistor, "unnamed[0]"],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # resistor.unnamed[1] ~ out.line
    _conn_resistor_to_out = fabll.MakeEdge(
        [resistor, "unnamed[1]"],
        [out, "line"],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # out.line ~ capacitor.unnamed[0]
    _conn_out_to_capacitor = fabll.MakeEdge(
        [out, "line"],
        [capacitor, "unnamed[0]"],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # capacitor.unnamed[1] ~ in_.reference.lv
    _conn_capacitor_to_gnd = fabll.MakeEdge(
        [capacitor, "unnamed[1]"],
        [in_, "reference", "lv"],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # Connect in_ and out references together
    _conn_references = fabll.MakeEdge(
        [in_, "reference"],
        [out, "reference"],
        edge=fbrk.EdgeInterfaceConnection.build(shallow=False),
    )

    # ----------------------------------------
    #            Expressions / Equations
    # ----------------------------------------
    # RC filter cutoff frequency: fc = 1 / (2 * pi * R * C)
    # Rearranged:
    #   C = 1 / (R * 2 * pi * fc)
    #   R = 1 / (C * 2 * pi * fc)

    # Literal for 2*pi
    _lit_two_pi = F.Literals.Numbers.MakeChild_SingleValue(
        value=2.0 * math.pi, unit=F.Units.Dimensionless
    )

    # R * C
    _mul_rc = F.Expressions.Multiply.MakeChild(
        [resistor, "resistance"], [capacitor, "capacitance"]
    )

    # 2 * pi * R * C
    _mul_two_pi_rc = F.Expressions.Multiply.MakeChild([_lit_two_pi], [_mul_rc])

    # Literal 1 for division
    _lit_one = F.Literals.Numbers.MakeChild_SingleValue(
        value=1.0, unit=F.Units.Dimensionless
    )

    # fc = 1 / (2 * pi * R * C)
    _div_fc = F.Expressions.Divide.MakeChild([_lit_one], [_mul_two_pi_rc])
    _eq_cutoff_frequency = F.Expressions.Is.MakeChild(
        [filter, "cutoff_frequency"], [_div_fc], assert_=True
    )

    # Set filter response to LOWPASS (this is an RC low-pass filter)
    _eq_response = F.Literals.AbstractEnums.MakeChild_SetSuperset(
        [filter, "response"], F.Filter.Response.LOWPASS
    )

    # Set filter order to 1 (first-order RC filter)
    _eq_order = F.Literals.Numbers.MakeChild_SetSingleton(
        [filter, "order"], 1.0, unit=F.Units.Dimensionless
    )

    # ----------------------------------------
    #            Usage Example
    # ----------------------------------------
    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
            import FilterElectricalRC, ElectricSignal, ElectricPower

            # Create low-pass RC filter
            rc_filter = new FilterElectricalRC
            rc_filter.filter.cutoff_frequency = 1kHz +/- 10%

            # Connect power reference (using reference_shim for convenience)
            power_supply = new ElectricPower
            assert power_supply.voltage within 5V +/- 5%
            rc_filter.reference_shim ~ power_supply

            # Connect input and output signals
            input_signal = new ElectricSignal
            output_signal = new ElectricSignal
            input_signal ~ rc_filter.in_
            rc_filter.out ~ output_signal

            """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )


# ----------------------------------------
#                 Tests
# ----------------------------------------


class TestFilterElectricalRC:
    """Tests for FilterElectricalRC solver equations."""

    def test_solves_resistance_from_c_and_fc(self):
        """
        Test that FilterElectricalRC correctly solves for resistance.

        Given: C = 100nF, fc = 1kHz
        Expected: R = 1 / (2 * pi * C * fc) ≈ 1591.5 Ω
        """
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.test.boundexpressions import BoundExpressions

        E = BoundExpressions()

        # Create the actual FilterElectricalRC module
        rc_filter = FilterElectricalRC.bind_typegraph(tg=E.tg).create_instance(g=E.g)

        # Set constraints: C = 100nF, fc = 1kHz
        C_value = 100e-9  # 100nF in Farads
        fc_value = 1000  # 1kHz in Hz

        # Get the parameter operands from the filter
        C_param = rc_filter.capacitor.get().capacitance.get().can_be_operand.get()
        fc_param = rc_filter.filter.get().cutoff_frequency.get().can_be_operand.get()
        R_param = rc_filter.resistor.get().resistance.get().can_be_operand.get()

        # Constrain C and fc
        E.is_subset(C_param, E.lit_op_single((C_value, E.U.Fa)), assert_=True)
        E.is_subset(fc_param, E.lit_op_single((fc_value, E.U.Hz)), assert_=True)

        # Manually calculate expected resistance: R = 1 / (2 * pi * C * fc)
        expected_R = 1 / (2 * math.pi * C_value * fc_value)

        # Run solver
        solver = Solver()
        solver.simplify_for(C_param, fc_param, R_param)

        # Get solver's result for R
        result = solver.extract_superset(
            R_param.as_parameter_operatable.force_get().as_parameter.force_get()
        )
        assert result is not None, "Solver should find resistance"

        # Get the Numbers node from the result
        result_numbers = fabll.Traits(result).get_obj_raw().try_cast(F.Literals.Numbers)
        assert result_numbers is not None, "Solver result should be Numbers"

        # Create expected Numbers and compare (equals handles tolerance)
        expected_numbers = E.numbers().setup_from_singleton(
            expected_R, unit=E._resolve_unit(E.U.Ohm)
        )
        assert result_numbers.op_setic_equals(expected_numbers, g=E.g, tg=E.tg), (
            f"Expected R ≈ {expected_R:.2f} Ω, got {result_numbers.pretty_str()}"
        )

    def test_solves_capacitance_from_r_and_fc(self):
        """
        Test that FilterElectricalRC correctly solves for capacitance.

        Given: R = 10kΩ, fc = 10kHz
        Expected: C = 1 / (2 * pi * R * fc) ≈ 1.59nF
        """
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.test.boundexpressions import BoundExpressions

        E = BoundExpressions()

        rc_filter = FilterElectricalRC.bind_typegraph(tg=E.tg).create_instance(g=E.g)

        # Set constraints: R = 10kΩ, fc = 10kHz
        R_value = 10000  # 10kΩ in Ohms
        fc_value = 10000  # 10kHz in Hz

        # Get the parameter operands
        C_param = rc_filter.capacitor.get().capacitance.get().can_be_operand.get()
        fc_param = rc_filter.filter.get().cutoff_frequency.get().can_be_operand.get()
        R_param = rc_filter.resistor.get().resistance.get().can_be_operand.get()

        # Constrain R and fc
        E.is_subset(R_param, E.lit_op_single((R_value, E.U.Ohm)), assert_=True)
        E.is_subset(fc_param, E.lit_op_single((fc_value, E.U.Hz)), assert_=True)

        # Manually calculate expected capacitance: C = 1 / (2 * pi * R * fc)
        expected_C = 1 / (2 * math.pi * R_value * fc_value)

        # Run solver
        solver = Solver()
        solver.simplify_for(R_param, fc_param, C_param)

        # Get solver's result for C
        result = solver.extract_superset(
            C_param.as_parameter_operatable.force_get().as_parameter.force_get()
        )
        assert result is not None, "Solver should find capacitance"

        # Get the Numbers node from the result
        result_numbers = fabll.Traits(result).get_obj_raw().try_cast(F.Literals.Numbers)
        assert result_numbers is not None, "Solver result should be Numbers"

        # Create expected Numbers and compare (equals handles tolerance)
        expected_numbers = E.numbers().setup_from_singleton(
            expected_C, unit=E._resolve_unit(E.U.Fa)
        )
        assert result_numbers.op_setic_equals(expected_numbers, g=E.g, tg=E.tg), (
            f"Expected C ≈ {expected_C:.2e} F, got {result_numbers.pretty_str()}"
        )

    def test_has_correct_response_and_order(self):
        """
        Test that FilterElectricalRC correctly sets filter response to LOWPASS
        and order to 1.
        """
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.test.boundexpressions import BoundExpressions

        E = BoundExpressions()

        rc_filter = FilterElectricalRC.bind_typegraph(tg=E.tg).create_instance(g=E.g)

        # Get the filter's response and order parameters
        response_param = rc_filter.filter.get().response.get()
        order_param = rc_filter.filter.get().order.get()

        # Run solver to resolve constraints
        solver = Solver()
        solver.simplify_for(
            response_param.can_be_operand.get(),
            order_param.can_be_operand.get(),
        )

        # Check response is constrained to LOWPASS
        response_result = solver.extract_superset(
            response_param.can_be_operand.get()
            .as_parameter_operatable.force_get()
            .as_parameter.force_get()
        )
        assert response_result is not None, "Solver should find response"
        response_enum = (
            fabll.Traits(response_result)
            .get_obj_raw()
            .try_cast(F.Literals.AbstractEnums)
        )
        assert response_enum is not None, "Response should be an enum literal"
        assert response_enum.get_values() == [F.Filter.Response.LOWPASS.value], (
            f"Expected LOWPASS, got {response_enum.get_values()}"
        )

        # Check order is constrained to 1
        order_result = solver.extract_superset(
            order_param.can_be_operand.get()
            .as_parameter_operatable.force_get()
            .as_parameter.force_get()
        )
        assert order_result is not None, "Solver should find order"
        order_numbers = (
            fabll.Traits(order_result).get_obj_raw().try_cast(F.Literals.Numbers)
        )
        assert order_numbers is not None, "Order should be a number literal"
        assert order_numbers.get_single() == 1.0, (
            f"Expected order = 1, got {order_numbers.get_single()}"
        )
