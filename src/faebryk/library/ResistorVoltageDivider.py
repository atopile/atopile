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


class _ResistorChain(fabll.Node):
    N = 2
    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    resistors = [F.Resistor.MakeChild() for _ in range(N)]
    terminals = [F.Electrical.MakeChild() for _ in range(2)]
    taps = [F.Electrical.MakeChild() for _ in range(N - 1)]
    total_resistance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)

    _connections = [
        fabll.is_interface.MakeConnectionEdge(
            [terminals[0]], [resistors[0], F.Resistor.unnamed[0]]
        ),
        fabll.is_interface.MakeConnectionEdge(
            [terminals[1]], [resistors[-1], F.Resistor.unnamed[1]]
        ),
        *[
            fabll.is_interface.MakeConnectionEdge(
                [tap],
                [r_prev, F.Resistor.unnamed[1]],
                [r_next, F.Resistor.unnamed[0]],
            )
            for tap, r_prev, r_next in zip(taps, resistors[:-1], resistors[1:])
        ],
    ]
    _asserts = [
        F.Expressions.Is.MakeChild(
            [total_resistance],
            [
                r_sum := F.Expressions.Add.MakeChild(
                    *[[r, F.Resistor.resistance] for r in resistors],
                )
            ],
            assert_=True,
        ),
    ]


class ResistorVoltageDivider(fabll.Node):
    """
    A voltage divider using two resistors.
    node[0] ~ resistor[1] ~ node[1] ~ resistor[2] ~ node[2]
    power.hv ~ node[0]
    power.lv ~ node[2]
    output.line ~ node[1]
    output.reference.lv ~ node[2]

    ```
       ref_in.hv
           |
        +--+--+
        | r0  |
        +--+--+
           |
           +------> ref_out.hv
           |
        +--+--+
        | r1  |
        +--+--+
           |
       ref_in.lv  | ref_out.lv
    ```
    """

    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # External interfaces
    ref_in = F.ElectricPower.MakeChild()
    ref_out = F.ElectricPower.MakeChild()

    # Components
    chain = _ResistorChain.MakeChild()

    # Variables
    v_in = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    v_out = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    total_resistance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)
    ratio = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)

    _connections = [
        fabll.is_interface.MakeConnectionEdge(
            [ref_in, F.ElectricPower.hv],
            [chain, _ResistorChain.terminals[0]],
        ),
        fabll.is_interface.MakeConnectionEdge(
            [ref_in, F.ElectricPower.lv],
            [ref_out, F.ElectricPower.lv],
            [chain, _ResistorChain.terminals[1]],
        ),
        fabll.is_interface.MakeConnectionEdge(
            [ref_out, F.ElectricPower.hv],
            [chain, _ResistorChain.taps[0]],
        ),
    ]

    _aliases = [
        F.Expressions.Is.MakeChild(
            [v_in],
            [ref_in, F.ElectricPower.voltage],
            assert_=True,
        ),
        F.Expressions.Is.MakeChild(
            [v_out],
            [ref_out, F.ElectricPower.voltage],
            assert_=True,
        ),
    ]

    # Link interface voltages to parameters
    _equations = [
        F.Expressions.Is.MakeChild(
            [total_resistance],
            [chain, _ResistorChain.total_resistance],
            assert_=True,
        ),
        F.Expressions.Is.MakeChild(
            [ratio],
            [
                _r_div := F.Expressions.Divide.MakeChild(
                    [chain, _ResistorChain.resistors[1], F.Resistor.resistance],
                    [total_resistance],
                )
            ],
            [
                _v_div := F.Expressions.Divide.MakeChild(
                    [v_out],
                    [v_in],
                )
            ],
            assert_=True,
        ),
        F.Expressions.Is.MakeChild(
            [current],
            [
                _v_r_div := F.Expressions.Divide.MakeChild(
                    [v_in],
                    [total_resistance],
                )
            ],
            assert_=True,
        ),
    ]

    # helper equations for the solver
    _rewrite_equations = [
        F.Expressions.Is.MakeChild(
            [total_resistance],
            [
                _v_i_div := F.Expressions.Divide.MakeChild(
                    [v_in],
                    [current],
                )
            ],
            assert_=True,
        ),
        F.Expressions.Is.MakeChild(
            [chain, _ResistorChain.resistors[1], F.Resistor.resistance],
            [
                _ratio_r_mul := F.Expressions.Multiply.MakeChild(
                    [ratio],
                    [total_resistance],
                )
            ],
            assert_=True,
        ),
    ]

    _net_name = fabll.Traits.MakeEdge(
        F.has_net_name_suggestion.MakeChild(
            name="VDIV_OUTPUT", level=F.has_net_name_suggestion.Level.SUGGESTED
        ),
        [ref_out, F.ElectricPower.lv],
    )


class VdivSolverTests:
    @pytest.mark.usefixtures("setup_project_config")
    @staticmethod
    def test_pick_adc_vdiv():
        """
        Test voltage divider for ADC input scaling.

        Divides ~10V supply down to ~3.1V for ADC input.

        Constraints:
          - v_in:  9.9V to 10.1V
          - v_out: 3.0V to 3.2V
          - max_current: 1mA to 2mA

        Expected result:
          - R = (V / I)
             =ss! 10V +/- 10% / {1mA..2mA}
             = {4.95kOhm..10.1kOhm}
          - ratio = (v_in / v_out)
             =ss! {3V..3.2V} / 10 +/- 10%
             = {3/10.1V..3.2/9.9V} = {0.297..0.323}
          - r_top = (R * ratio)
             =ss! {4.95kOhm..10.1kOhm} * {0.297..0.323}
             = {1.47kOhm..3.26kOhm}
          - r_bottom = (R - r_top)
             =ss! {4.95kOhm..10.1kOhm} - {1.47kOhm..3.26kOhm}
             = {1.69kOhm..8.63kOhm}
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
            adc_ref = F.ElectricPower.MakeChild()

        app = _App.bind_typegraph(tg=tg).create_instance(g=g)

        # Connect interfaces
        app.supply.get()._is_interface.get().connect_to(app.rdiv.get().ref_in.get())
        app.rdiv.get().ref_out.get()._is_interface.get().connect_to(app.adc_ref.get())

        # Set constraints
        E.is_subset(
            app.supply.get().voltage.get().can_be_operand.get(),
            E.lit_op_range(((9.9, E.U.V), (10.1, E.U.V))),
            assert_=True,
        )
        E.is_subset(
            app.adc_ref.get().voltage.get().can_be_operand.get(),
            E.lit_op_range(((3.0, E.U.V), (3.2, E.U.V))),
            assert_=True,
        )
        E.is_subset(
            app.rdiv.get().current.get().can_be_operand.get(),
            E.lit_op_range(((1, E.U.mA), (2, E.U.mA))),
            assert_=True,
        )

        F.is_alias_bus_parameter.resolve_bus_parameters(g=g, tg=tg)
        solver = Solver()
        pick_part_recursively(app, solver)

        r_top = (
            app.rdiv.get()
            .chain.get()
            .resistors[0]
            .get()
            .resistance.get()
            .is_parameter_operatable.get()
            .force_extract_subset(F.Literals.Numbers)
        )
        r_bottom = (
            app.rdiv.get()
            .chain.get()
            .resistors[1]
            .get()
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

        rdiv = ResistorVoltageDivider.bind_typegraph(tg=tg).create_instance(g=g)

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

        rdiv = ResistorVoltageDivider.bind_typegraph(tg=tg).create_instance(g=g)

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
            rdiv.current.get().can_be_operand.get(),
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

        rdiv = ResistorVoltageDivider.bind_typegraph(tg=tg).create_instance(g=g)

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
            rdiv.current.get().can_be_operand.get(),
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
        vdiv = ResistorVoltageDivider.bind_instance(
            not_none(
                fbrk.EdgeComposition.get_child_by_identifier(
                    bound_node=app_instance, child_identifier="vdiv"
                )
            )
        )
        r_top = vdiv.chain.get().resistors[0].get()
        r_bottom = vdiv.chain.get().resistors[1].get()
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
                    assert vdiv.current within 1mA to 3mA
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
        vdiv = ResistorVoltageDivider.bind_instance(
            not_none(
                fbrk.EdgeComposition.get_child_by_identifier(
                    bound_node=app_instance, child_identifier="vdiv"
                )
            )
        )
        r_top = vdiv.chain.get().resistors[0].get()
        r_bottom = vdiv.chain.get().resistors[1].get()
        assert r_top.has_trait(F.Pickable.has_part_picked)
        assert r_bottom.has_trait(F.Pickable.has_part_picked)
