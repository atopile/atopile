# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none

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


class VdivSolverTests:
    @pytest.mark.usefixtures("setup_project_config")
    @staticmethod
    def test_pick_adc_vdiv():
        """
        Test voltage divider for ADC input scaling.

        Divides ~10V supply down to ~3.1V for ADC input.

                    supply (9.9V - 10.1V)
                         |
                      +--+--+
                      | hv  |
                      | r_t |
                      +--+--+
                         +------> adc_input (3.0V - 3.2V)
                         |
                      +--+--+
                      | r_b |
                      | lv  |
                      +--+--+
                         |
                        GND

        Constraints:
          - v_in:  9.9V to 10.1V
          - v_out: 3.0V to 3.2V
          - max_current: 1mA to 2mA

        Expected result:
          - V / I = R ss! 10V +/- 10% / {1mA..2mA} = {4.5kOhm..11kOhm}
          - ratio = v_in / v_out ss! {3V..3.2V} / 10 +/- 10% = {3/11V..3.2/9V} = {0.273..0.356}
          - r_top = r_total * ratio ss! {4.5kOhm..11kOhm} * {0.273..0.356} = {1.23kOhm..3.95kOhm}
          - r_bottom = r_total - r_top ss! {4.5kOhm..11kOhm} - {1.23kOhm..3.95kOhm} = {3.27kOhm..7.05kOhm}
        """
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.picker.picker import pick_part_recursively
        from faebryk.libs.test.boundexpressions import BoundExpressions

        E = BoundExpressions()
        g, tg = E.g, E.tg

        class _App(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            supply = F.ElectricPower.MakeChild()
            rdiv = ResistorVoltageDivider.MakeChild()
            adc_input = F.ElectricSignal.MakeChild()

        app = _App.bind_typegraph(tg=tg).create_instance(g=g)

        # Connect interfaces
        app.supply.get()._is_interface.get().connect_to(app.rdiv.get().power.get())
        app.rdiv.get().output.get()._is_interface.get().connect_to(app.adc_input.get())

        # Set constraints
        E.is_subset(
            app.supply.get().voltage.get().can_be_operand.get(),
            E.lit_op_range(((9.9, E.U.V), (10.1, E.U.V))),
            assert_=True,
        )
        E.is_subset(
            app.adc_input.get().reference.get().voltage.get().can_be_operand.get(),
            E.lit_op_range(((3.0, E.U.V), (3.2, E.U.V))),
            assert_=True,
        )
        E.is_subset(
            app.rdiv.get().max_current.get().can_be_operand.get(),
            E.lit_op_range(((1, E.U.mA), (2, E.U.mA))),
            assert_=True,
        )

        solver = Solver()
        pick_part_recursively(app, solver)

        r_top = (
            app.rdiv.get()
            .r_top.get()
            .resistance.get()
            .is_parameter_operatable.get()
            .force_extract_subset(F.Literals.Numbers)
        )
        r_bottom = (
            app.rdiv.get()
            .r_bottom.get()
            .resistance.get()
            .is_parameter_operatable.get()
            .force_extract_subset(F.Literals.Numbers)
        )

        print(r_top, r_bottom)

    @pytest.mark.slow
    @pytest.mark.usefixtures("setup_project_config")
    @staticmethod
    def test_pick_dependency_advanced_1():
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.picker.picker import pick_part_recursively
        from faebryk.libs.test.boundexpressions import BoundExpressions

        E = BoundExpressions()
        g, tg = E.g, E.tg

        rdiv = F.ResistorVoltageDivider.bind_typegraph(tg=tg).create_instance(g=g)

        E.is_subset(
            rdiv.total_resistance.get().can_be_operand.get(),
            E.lit_op_range_from_center_rel((100, E.U.kOhm), 0.1),
            assert_=True,
        )
        E.is_subset(
            rdiv.ratio.get().can_be_operand.get(),
            E.lit_op_range_from_center_rel((0.1, E.U.dl), 0.2),
            assert_=True,
        )

        solver = Solver()
        pick_part_recursively(rdiv, solver)

    @pytest.mark.slow
    @pytest.mark.usefixtures("setup_project_config")
    @staticmethod
    def test_pick_dependency_advanced_2():
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.picker.picker import pick_part_recursively
        from faebryk.libs.test.boundexpressions import BoundExpressions

        E = BoundExpressions()
        g, tg = E.g, E.tg

        rdiv = F.ResistorVoltageDivider.bind_typegraph(tg=tg).create_instance(g=g)

        E.is_subset(
            rdiv.v_in.get().can_be_operand.get(),
            E.lit_op_range_from_center_rel((10, E.U.V), 0.1),
            assert_=True,
        )
        E.is_subset(
            rdiv.v_out.get().can_be_operand.get(),
            E.lit_op_range(((3, E.U.V), (3.2, E.U.V))),
            assert_=True,
        )
        E.is_subset(
            rdiv.max_current.get().can_be_operand.get(),
            E.lit_op_range(((1, E.U.mA), (3, E.U.mA))),
            assert_=True,
        )

        solver = Solver()
        pick_part_recursively(rdiv, solver)

    @pytest.mark.slow
    @pytest.mark.usefixtures("setup_project_config")
    @staticmethod
    def test_pick_dependency_div_negative():
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.picker.picker import pick_part_recursively
        from faebryk.libs.test.boundexpressions import BoundExpressions

        E = BoundExpressions()
        g, tg = E.g, E.tg

        rdiv = F.ResistorVoltageDivider.bind_typegraph(tg=tg).create_instance(g=g)

        E.is_subset(
            rdiv.v_in.get().can_be_operand.get(),
            E.lit_op_range(((-10, E.U.V), (-9, E.U.V))),
            assert_=True,
        )
        E.is_subset(
            rdiv.v_out.get().can_be_operand.get(),
            E.lit_op_range(((-3.2, E.U.V), (-3, E.U.V))),
            assert_=True,
        )
        E.is_subset(
            rdiv.max_current.get().can_be_operand.get(),
            E.lit_op_range(((1, E.U.mA), (3, E.U.mA))),
            assert_=True,
        )

        solver = Solver()
        pick_part_recursively(rdiv, solver)

    @pytest.mark.slow
    @pytest.mark.usefixtures("setup_project_config")
    @staticmethod
    def test_ato_pick_resistor_voltage_divider_ato(tmp_path: Path):
        import textwrap

        from atopile.compiler.build import Linker, StdlibRegistry, build_file
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.picker.picker import pick_part_recursively

        # Note: Using ResistorVoltageDivider directly instead of inheriting
        # because `module VDiv from ResistorVoltageDivider` inheritance
        # doesn't properly copy children from Python-defined parent classes yet.
        main_path = tmp_path / "main.ato"
        main_path.write_text(
            textwrap.dedent(
                """
                import ResistorVoltageDivider

                module App:
                    vdiv = new ResistorVoltageDivider

                    vdiv.v_in = 10V +/- 1%
                    assert vdiv.v_out within 3V to 3.2V
                """
            ),
            encoding="utf-8",
        )

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        stdlib = StdlibRegistry(tg)

        result = build_file(g=g, tg=tg, import_path="main.ato", path=main_path)
        assert "App" in result.state.type_roots

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        # Instantiate and pick
        app_type = result.state.type_roots["App"]
        app_instance = tg.instantiate_node(type_node=app_type, attributes={})

        solver = Solver()
        pick_part_recursively(fabll.Node.bind_instance(app_instance), solver)

        # Check all resistors have parts picked
        vdiv = F.ResistorVoltageDivider.bind_instance(
            not_none(
                fbrk.EdgeComposition.get_child_by_identifier(
                    bound_node=app_instance, child_identifier="vdiv"
                )
            )
        )
        r_top = vdiv.r_top.get()
        r_bottom = vdiv.r_bottom.get()
        assert r_top.has_trait(F.Pickable.has_part_picked)
        assert r_bottom.has_trait(F.Pickable.has_part_picked)

    @pytest.mark.slow
    @pytest.mark.usefixtures("setup_project_config")
    @staticmethod
    def test_ato_pick_resistor_voltage_divider_fab():
        import textwrap

        from atopile.compiler.build import Linker, StdlibRegistry, build_source
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.picker.picker import pick_part_recursively
        from faebryk.libs.test.boundexpressions import BoundExpressions

        E = BoundExpressions()
        g, tg = E.g, E.tg
        stdlib = StdlibRegistry(tg)

        result = build_source(
            g=g,
            tg=tg,
            source=textwrap.dedent(
                """
                import ResistorVoltageDivider

                module App:
                    vdiv = new ResistorVoltageDivider

                    vdiv.v_in = 10V +/- 1%
                    assert vdiv.v_out within 3V to 3.2V
                    assert vdiv.max_current within 1mA to 3mA
                """
            ),
        )
        assert "App" in result.state.type_roots

        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)

        # Instantiate and pick
        app_type = result.state.type_roots["App"]
        app_instance = tg.instantiate_node(type_node=app_type, attributes={})

        solver = Solver()
        pick_part_recursively(fabll.Node.bind_instance(app_instance), solver)

        # Check all resistors have parts picked
        vdiv = F.ResistorVoltageDivider.bind_instance(
            not_none(
                fbrk.EdgeComposition.get_child_by_identifier(
                    bound_node=app_instance, child_identifier="vdiv"
                )
            )
        )
        r_top = vdiv.r_top.get()
        r_bottom = vdiv.r_bottom.get()
        assert r_top.has_trait(F.Pickable.has_part_picked)
        assert r_bottom.has_trait(F.Pickable.has_part_picked)
