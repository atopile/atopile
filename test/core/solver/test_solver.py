# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from itertools import pairwise
from typing import Callable, cast

import pytest

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.mutator import MutationMap
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.utils import (
    Contradiction,
    ContradictionByLiteral,
)
from faebryk.libs.picker.picker import pick_part_recursively
from faebryk.libs.test.boundexpressions import BoundExpressions
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)

_Unit = type[fabll.NodeT]
_Quantity = tuple[float, _Unit]
_Range = tuple[float, float] | tuple[_Quantity, _Quantity]

Range = F.Literals.Numbers

dimensionless = F.Units.Dimensionless


def _create_letters(
    E: BoundExpressions, n: int, units: type[fabll.Node] | None = None
) -> tuple[F.Parameters.ReprContext, list[F.Parameters.is_parameter_operatable]]:
    context = F.Parameters.ReprContext()
    if units is None:
        units = E.U.dl

    class _App(fabll.Node):
        params = [
            F.Parameters.NumericParameter.MakeChild(
                unit=units, domain=F.NumberDomain.Args(negative=True)
            )
            for _ in range(n)
        ]

    app = _App.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    params = [p.get().is_parameter_operatable.get() for p in app.params]

    return context, params


def _extract(
    op: F.Parameters.can_be_operand,
    res: MutationMap | Solver,
    domain_default: bool = False,
) -> F.Literals.is_literal:
    if not isinstance(res, MutationMap):
        assert domain_default
        return res.simplify_and_extract_superset(
            op.as_parameter_operatable.force_get().as_parameter.force_get()
        )
    return not_none(
        res.try_extract_superset(
            op.as_parameter_operatable.force_get(),
            domain_default=domain_default,
        )
    )


def _extract_and_check(
    op: F.Parameters.can_be_operand,
    res: MutationMap | DefaultSolver,
    expected: F.Parameters.can_be_operand
    | F.Literals.LiteralValues
    | F.Literals.LiteralNodes
    | F.Literals.is_literal,
    domain_default: bool = True,
) -> bool:
    extracted = _extract(op, res, domain_default=domain_default)
    ctx = (
        res.print_ctx
        if isinstance(res, MutationMap)
        else not_none(res.state).data.mutation_map.print_ctx
    )
    if isinstance(expected, F.Literals.is_literal):
        expected = expected.as_operand.get()
    if isinstance(expected, F.Literals.LiteralNodes):
        expected = expected.can_be_operand.get()
    if not isinstance(expected, F.Parameters.can_be_operand):
        matches = extracted.equals_singleton(expected)
        if not matches:
            print(
                f"Expected {expected}"
                f" but got {extracted.pretty_str()}"
                f"\nfor op: {op.as_parameter_operatable.force_get().compact_repr(ctx)}"
            )
        return matches

    matches = extracted.equals(expected.as_literal.force_get())
    if not matches:
        print(
            f"Expected {expected.as_literal.force_get().pretty_str()}"
            f" but got {extracted.pretty_str()}"
            f"\nfor op: {op.pretty()}"
        )
    return matches


def test_solve_phase_one():
    solver = DefaultSolver()
    E = BoundExpressions()

    class _App(fabll.Node):
        voltage1 = F.Parameters.NumericParameter.MakeChild(unit=E.U.V)
        voltage2 = F.Parameters.NumericParameter.MakeChild(unit=E.U.V)
        voltage3 = F.Parameters.NumericParameter.MakeChild(unit=E.U.V)

    app = _App.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    voltage1_op = app.voltage1.get().can_be_operand.get()
    voltage2_op = app.voltage2.get().can_be_operand.get()
    voltage3_op = app.voltage3.get().can_be_operand.get()

    E.is_(voltage1_op, voltage2_op, assert_=True)
    E.is_(voltage3_op, E.add(voltage1_op, voltage2_op), assert_=True)

    E.is_subset(voltage1_op, E.lit_op_range(((1, E.U.V), (3, E.U.V))), assert_=True)
    E.is_subset(voltage3_op, E.lit_op_range(((2, E.U.V), (6, E.U.V))), assert_=True)

    repr_map = solver.simplify(E.tg, E.g).data.mutation_map

    # voltage1 and voltage2 are aliased, so they should have the same value
    assert _extract_and_check(
        voltage1_op, repr_map, E.lit_op_range(((1, E.U.V), (3, E.U.V)))
    )
    assert _extract_and_check(
        voltage2_op, repr_map, E.lit_op_range(((1, E.U.V), (3, E.U.V)))
    )
    # voltage3 = voltage1 + voltage2 = 2 * [1V, 3V] = [2V, 6V]
    assert _extract_and_check(
        voltage3_op, repr_map, E.lit_op_range(((2, E.U.V), (6, E.U.V)))
    )


def test_simplify():
    """
    (((((((((((A + B + 1) + C + 2) * D * 3) * E * 4) * F * 5) * G * (A - A)) + H + 7)
    + I + 8) + J + {0..1}) - 3) - 4) <=! 11
    => (H + I + J + {8..9}) ss! {0..11}
    """
    E = BoundExpressions()

    class _App(fabll.Node):
        ops = [F.Parameters.NumericParameter.MakeChild(unit=E.U.dl) for _ in range(10)]

    app_type = _App.bind_typegraph(tg=E.tg)
    app = app_type.create_instance(g=E.g)

    app_ops = [p.get().can_be_operand.get() for p in app.ops]
    constants: list[F.Parameters.can_be_operand] = [
        E.lit_op_single((c, E.U.dl)) for c in range(0, 10)
    ]
    constants[6] = E.subtract(app_ops[0], app_ops[0])
    constants[9] = E.lit_op_range(((0, E.U.dl), (1, E.U.dl)))

    acc = app.ops[0].get().can_be_operand.get()
    for i, p in enumerate(app_ops[1:3]):
        acc = E.add(acc, E.add(p, constants[i]))
    for i, p in enumerate(app_ops[3:7]):
        acc = E.multiply(acc, E.multiply(p, constants[i + 3]))
    for i, p in enumerate(app_ops[7:]):
        acc = E.add(acc, E.add(p, constants[i + 7]))

    acc = E.subtract(acc, E.lit_op_single((3, E.U.dl)), E.lit_op_single((4, E.U.dl)))
    le = E.less_or_equal(acc, E.lit_op_single((11, E.U.dl)), assert_=True)

    solver = DefaultSolver()
    res = solver.simplify(E.tg, E.g).data.mutation_map
    out = res.map_forward(le.as_parameter_operatable.force_get()).maps_to

    assert out
    out_ss = fabll.Traits(out).get_obj(F.Expressions.IsSubset)
    assert out_ss.has_trait(F.Expressions.is_predicate)
    out_add_e = next(
        iter(out_ss.is_expression.get().get_operand_operatables())
    ).as_expression.force_get()
    assert fabll.Traits(out_add_e).get_obj_raw().isinstance(F.Expressions.Add)
    lits = out_add_e.get_operand_literals().values()
    assert len(lits) == 1
    lit = next(iter(lits))
    assert lit.equals(
        E.lit_op_range(((8, E.U.dl), (9, E.U.dl))).as_literal.force_get()
    ), f"lit: {lit.pretty_str()} != {{8..9}}"
    H_mapped = res.map_forward(app.ops[7].get().is_parameter_operatable.get()).maps_to
    I_mapped = res.map_forward(app.ops[8].get().is_parameter_operatable.get()).maps_to
    J_mapped = res.map_forward(app.ops[9].get().is_parameter_operatable.get()).maps_to
    assert H_mapped
    assert I_mapped
    assert J_mapped
    out_ops = out_add_e.get_operand_operatables()
    assert len(out_ops) == 3
    assert set(out_ops) == {H_mapped, I_mapped, J_mapped}


def test_simplify_logic_and():
    """
    X = And(And(And(And(p0, True), p1), p2), p3)
    Y = And!(X, X)
    => Y = Not!(Or(Not(p0), Not(p1), Not(p2), Not(p3)))
    => p0!, p1!, p2!, p3!
    """
    E = BoundExpressions()

    class _App(fabll.Node):
        p = [F.Parameters.BooleanParameter.MakeChild() for _ in range(4)]

    app_type = _App.bind_typegraph(tg=E.tg)
    app = app_type.create_instance(g=E.g)

    p_ops = [p.get().can_be_operand.get() for p in app.p]

    anded = E.and_(p_ops[0], E.lit_bool(True))

    for p_op in p_ops[1:]:
        anded = E.and_(anded, p_op)

    anded = E.and_(anded, anded, assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g, relevant=p_ops).data.mutation_map

    # Y = And!(X, X) canonicalizes to Not!(Or(Not(p0), Not(p1), Not(p2), Not(p3)))
    # which simplifies to Not(false) = true (the assertion is satisfied)
    Y_mapped = repr_map.map_forward(anded.as_parameter_operatable.force_get()).maps_to
    assert Y_mapped

    # Y_mapped should be Not(false) = true
    not_expr = fabll.Traits(Y_mapped).get_obj(F.Expressions.Not)

    # TODO more checking on not_expr
    _ = not_expr

    # The parameters should still be tracked as BooleanParameters
    for p_op in p_ops:
        mapped = repr_map.map_forward(p_op.as_parameter_operatable.force_get()).maps_to
        assert mapped is not None
        assert (
            fabll.Traits(mapped).get_obj_raw().isinstance(F.Parameters.BooleanParameter)
        )


def test_shortcircuit_logic_and():
    """
    And!(p0, False)
    => Contradiction
    """
    E = BoundExpressions()
    p0 = E.bool_parameter_op()
    E.and_(p0, E.lit_bool(False), assert_=True)
    solver = DefaultSolver()

    with pytest.raises(ContradictionByLiteral):
        solver.simplify(E.tg, E.g)


def test_shortcircuit_logic_or():
    """
    X := Or(*App.p[0:3], True)
    Y := Or(X, X)
    Y -> True
    """
    E = BoundExpressions()

    class _App(fabll.Node):
        p = [F.Parameters.BooleanParameter.MakeChild() for _ in range(4)]

    app = _App.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    p_ops = [p.get().can_be_operand.get() for p in app.p]

    X = E.or_(p_ops[0], E.lit_bool(True))
    for p in p_ops[1:]:
        X = E.or_(X, p)
    Y = E.or_(X, X)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    assert _extract_and_check(Y, repr_map, True)


def test_inequality_to_set():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.dl)
    E.less_than(p0, E.lit_op_single((2, E.U.dl)), assert_=True)
    E.greater_than(p0, E.lit_op_single((1, E.U.dl)), assert_=True)
    solver = DefaultSolver()
    assert _extract_and_check(p0, solver, E.lit_op_range((1, 2)))


def test_remove_obvious_tautologies():
    """
    p0 is! p1 + p2
    p1 >= 0
    p2 >= 0
    p0 is! p1 + p2
    p2 is! p2
    => remove p2 is! p2
    """
    E = BoundExpressions()
    p0, p1, p2 = [E.parameter_op(units=E.U.dl) for _ in range(3)]

    E.is_(p0, E.add(p1, p2), assert_=True)

    E.greater_than(p1, E.lit_op_single((0.0, E.U.dl)), assert_=True)
    E.greater_than(p2, E.lit_op_single((0.0, E.U.dl)), assert_=True)
    E.is_(p2, E.add(p1, p2), assert_=True)
    X = E.is_(p2, p2, assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map

    # The tautology X = (p2 is! p2) gets simplified to Is(p2) with single operand
    out = repr_map.map_forward(X.as_parameter_operatable.force_get())
    assert out is not None and out.maps_to is not None

    # The Is expression should have been simplified to have only 1 operand (identity)
    is_expr = fabll.Traits(out.maps_to).get_obj(F.Expressions.Is)
    operands = is_expr.is_expression.get().get_operands()
    assert len(operands) == 1  # Simplified from Is(p2, p2) to Is(p2)


def test_subset_of_literal():
    E = BoundExpressions()
    p0, p1, p2 = (
        E.parameter_op(
            units=E.U.dl,
            within=E.lit_op_range((0, i)).get_parent_of_type(F.Literals.Numbers),
        )
        for i in range(3)
    )
    E.is_(p0, p1, assert_=True)
    E.is_(p1, p2, assert_=True)

    solver = DefaultSolver()
    solver.simplify(E.g, E.tg, relevant=[p0, p1, p2])

    # for p in (p0, p1, p2):
    #     assert solver.inspect_get_known_supersets(
    #         p.as_parameter.force_get()
    #     ) == E.lit_op_range((0.0, 0.0))


def test_alias_classes():
    """
    A is! B
    addition = C + D
    B is! addition
    addition2 = D + C
    H is! addition2
    """
    E = BoundExpressions()
    A, B, C, D, H = (E.parameter_op() for _ in range(5))
    E.is_(A, B, assert_=True)
    addition = E.add(C, D)
    E.is_(B, addition, assert_=True)
    addition2 = E.add(D, C)
    E.is_(H, addition2, assert_=True)

    context = F.Parameters.ReprContext()
    for p in (A, B, C, D, H):
        p.as_parameter_operatable.force_get().compact_repr(context)
    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g, print_context=context).data.mutation_map

    # A, B, and H are aliased via the Is constraints and commutativity of addition
    # A is! B, B is! (C+D), H is! (D+C) where C+D == D+C
    A_mapped = repr_map.map_forward(A.as_parameter_operatable.force_get()).maps_to
    B_mapped = repr_map.map_forward(B.as_parameter_operatable.force_get()).maps_to
    H_mapped = repr_map.map_forward(H.as_parameter_operatable.force_get()).maps_to
    addition_mapped = repr_map.map_forward(
        addition.as_parameter_operatable.force_get()
    ).maps_to
    addition2_mapped = repr_map.map_forward(
        addition2.as_parameter_operatable.force_get()
    ).maps_to

    # A and B should be unified (same parameter)
    assert A_mapped == B_mapped

    # C + D and D + C should be unified (commutativity)
    assert addition_mapped == addition2_mapped

    # A, B, H should all be unified since they're all aliased to the same Add expression
    assert A_mapped == B_mapped == H_mapped


@pytest.mark.usefixtures("setup_project_config")
@pytest.mark.skip(reason="TODO: Replace with new realworld test")
def test_solve_realworld_biggest():
    pass
    # TODO: Replace with new realworld test

    # class App(fabll.Node):
    #     led = fabll.f_field(F.PoweredLED)(low_side_resistor=True)
    #     mcu: RP2040_ReferenceDesign
    #     usb_power: USB_C_PSU_Vertical

    #     def __preinit__(self):
    #         self.led.led.color.constrain_subset(F.LED.Color.YELLOW)
    #         self.led.led.brightness.constrain_subset(
    #             TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
    #         )

    #         self.usb_power.power_out.connect(self.mcu.usb.usb_if.buspower)
    #         self.mcu.rp2040.gpio[25].line.connect(self.led.power.hv)
    #         self.usb_power.power_out.lv.connect(self.led.power.lv)
    #         self.mcu.rp2040.pinmux.enable(self.mcu.rp2040.gpio[25])

    # app = App()
    # F.is_bus_parameter.resolve_bus_parameters(app.get_graph())
    # solver = DefaultSolver()
    # solver.simplify(app.get_graph())

    # pick_part_recursively(app, solver)


def test_inspect_known_superranges():
    E = BoundExpressions()
    p0 = E.parameter_op(
        units=E.U.V,
        within=E.lit_op_range(((1, E.U.V), (10, E.U.V))).get_parent_of_type(
            F.Literals.Numbers
        ),
    )
    E.is_(
        p0,
        E.add(
            E.lit_op_range(((1, E.U.V), (3, E.U.V))),
            E.lit_op_range(((4, E.U.V), (6, E.U.V))),
        ),
        assert_=True,
    )
    solver = DefaultSolver()
    assert _extract_and_check(p0, solver, E.lit_op_range(((5, E.U.V), (9, E.U.V))))


def test_obvious_contradiction_by_literal():
    """
    p0 is! [0V, 10V]
    p1 is! [5V, 10V]
    p0 is! p1
    """
    E = BoundExpressions()
    p0, p1 = [E.parameter_op(units=E.U.V) for _ in range(2)]

    E.is_subset(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)
    E.is_subset(p1, E.lit_op_range(((5, E.U.V), (10, E.U.V))), assert_=True)

    E.is_(p0, p1, assert_=True)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify(E.tg, E.g)


def test_subset_is():
    """
    A is! [0, 15]
    B ss! [5, 20]
    A is! B
    => Contradiction
    """
    E = BoundExpressions()
    A, B = [E.parameter_op() for _ in range(2)]

    E.is_subset(A, E.lit_op_range((0, 15)), assert_=True)
    E.is_subset(B, E.lit_op_range((5, 20)), assert_=True)
    E.is_(A, B, assert_=True)

    context = F.Parameters.ReprContext()
    for p in [A, B]:
        p.as_parameter_operatable.force_get().compact_repr(context)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify(E.tg, E.g)


def test_subset_is_expr():
    E = BoundExpressions()
    A, B, C = [E.parameter_op() for _ in range(3)]

    context = F.Parameters.ReprContext()
    for p in [A, B, C]:
        p.as_parameter_operatable.force_get().compact_repr(context)

    D = E.add(A, B)
    E.is_subset(C, E.lit_op_range((0, 15)), assert_=True)

    E.is_subset(D, E.lit_op_range((5, 20)), assert_=True)

    E.is_(C, D, assert_=True)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify(E.tg, E.g, print_context=context)


def test_subset_single_alias():
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.V)

    E.is_subset(A, E.lit_op_single((1, E.U.V)), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    assert _extract_and_check(A, repr_map, E.lit_op_single((1, E.U.V)))


def test_very_simple_alias_class():
    """
    A is! B
    B is! C
    A is! [1V, 2V]
    => B is! [1V, 2V], C is! [1V, 2V]
    """
    E = BoundExpressions()
    A, B, C = params = (E.parameter_op(units=E.U.V) for _ in range(3))
    E.is_(A, B, assert_=True)
    E.is_(B, C, assert_=True)
    E.is_subset(A, E.lit_op_range(((1, E.U.V), (2, E.U.V))), assert_=True)

    context = F.Parameters.ReprContext()
    for p in params:
        p.as_parameter_operatable.force_get().compact_repr(context)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    A_res = _extract(A, repr_map)
    B_res = _extract(B, repr_map)
    C_res = _extract(C, repr_map)
    assert A_res.equals(B_res)
    assert B_res.equals(C_res)
    assert A_res.equals(C_res)


def test_domain():
    """
    p0 within [0V, 10V]
    p0 is! [15V, 20V]
    => Contradiction
    """
    E = BoundExpressions()
    p0 = E.parameter_op(
        units=E.U.V,
        within=E.lit_op_range(((0, E.U.V), (10, E.U.V))).get_parent_of_type(
            F.Literals.Numbers
        ),
    )
    E.is_subset(p0, E.lit_op_range(((15, E.U.V), (20, E.U.V))), assert_=True)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify(E.tg, E.g)


def test_less_obvious_contradiction_by_literal():
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.V)
    B = E.parameter_op(units=E.U.V)
    C = E.parameter_op(units=E.U.V)

    E.is_subset(A, E.lit_op_range(((0.0, E.U.V), (10.0, E.U.V))), assert_=True)
    E.is_subset(B, E.lit_op_range(((5.0, E.U.V), (10.0, E.U.V))), assert_=True)
    E.is_(C, E.add(A, B), assert_=True)
    E.is_subset(E.lit_op_range(((0.0, E.U.V), (15.0, E.U.V))), C, assert_=True)

    print_context = F.Parameters.ReprContext()
    for p in (A, B, C):
        p.as_parameter_operatable.force_get().compact_repr(print_context)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify(E.tg, E.g, print_context=print_context)


def test_symmetric_inequality_correlated():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    p1 = E.parameter_op(units=E.U.V)

    lit = E.lit_op_range(((0, E.U.V), (10, E.U.V)))
    E.is_subset(p0, lit, assert_=True)
    E.is_(p1, p0, assert_=True)

    E.greater_or_equal(p0, p1, assert_=True)
    E.greater_or_equal(p1, p0, assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    p0_lit = _extract(p0, repr_map)
    p1_lit = _extract(p1, repr_map)
    assert p0_lit.equals(p1_lit)
    assert p0_lit.equals(lit.as_literal.force_get())


@pytest.mark.parametrize(
    "expr_type, operands, expected",
    [
        (F.Expressions.Add.c, (5, 10), 15),
        # (Subtract, (5, 10), -5),
        # (Multiply, (5, 10), 50),
        # (Divide, (5, 10), 0.5),
    ],
)
def test_simple_literal_folds_arithmetic(
    expr_type: Callable[..., F.Parameters.can_be_operand],
    operands: tuple[float, ...],
    expected: float,
):
    E = BoundExpressions()
    expected_result = expected

    p0 = E.parameter_op(units=E.U.dl)
    p1 = E.parameter_op(units=E.U.dl)

    E.is_subset(p0, E.lit_op_single(operands[0]), assert_=True)
    E.is_subset(p1, E.lit_op_single(operands[1]), assert_=True)

    expr = expr_type(p0, p1)
    E.less_or_equal(expr, E.lit_op_single(100.0), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    assert _extract_and_check(expr, repr_map, expected_result, allow_subset=True)


@pytest.mark.parametrize(
    "expr_type, operands, expected",
    [
        (F.Expressions.Add.c, (5, 10), 15),
        (F.Expressions.Add.c, (-5, 15), 10),
        # (F.Expressions.Add.c, ((0, 10), 5), (5, 15)),
        # (F.Expressions.Add.c, ((0, 10), (-10, 0)), (-10, 10)),
        (F.Expressions.Add.c, (5, 5, 5), 15),
        (F.Expressions.Subtract.c, (5, 10), -5),
        (F.Expressions.Multiply.c, (5, 10), 50),
        (F.Expressions.Divide.c, (5, 10), 0.5),
    ],
)
def test_super_simple_literal_folding(
    expr_type: Callable[[F.Parameters.can_be_operand], F.Parameters.can_be_operand],
    operands: tuple[float, ...],
    expected: float,
):
    E = BoundExpressions()
    operands_op = [E.lit_op_single(o) for o in operands]
    expr = expr_type(*operands_op)
    solver = DefaultSolver()

    E.less_or_equal(expr, E.lit_op_single(100.0), assert_=True)

    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    assert _extract_and_check(expr, repr_map, expected)


def test_literal_folding_add_multiplicative_1():
    """
    expr := (A + (A * 2) + (A * 5) + B + (A * B * 2)) - B
    expr <=! 100 # need predicate for solver
    => 8A + 2AB
    """
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.dl)
    B = E.parameter_op(units=E.U.dl)

    expr = E.subtract(
        E.add(
            A,
            E.multiply(A, E.lit_op_single(2)),
            E.multiply(A, E.lit_op_single(5)),
            B,
            E.multiply(A, B, E.lit_op_single(2)),
        ),
        B,
    )
    # expect: 8A + 2AB

    E.less_or_equal(expr, E.lit_op_single(100.0), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map

    rep_add = not_none(
        repr_map.map_forward(expr.as_parameter_operatable.force_get()).maps_to
    )
    rep_A = repr_map.map_forward(A.as_parameter_operatable.force_get()).maps_to
    rep_B = repr_map.map_forward(B.as_parameter_operatable.force_get()).maps_to
    assert rep_A is not None
    assert rep_B is not None

    context = repr_map.print_ctx
    operands = (
        fabll.Traits(rep_add)
        .get_obj(F.Expressions.Add)
        .is_expression.get()
        .get_operands()
    )
    assert len(operands) == 2, f"{rep_add.compact_repr(context)}"
    mul1, mul2 = operands

    mulexp1 = fabll.Traits(mul1).get_obj(F.Expressions.Multiply)
    mulexp2 = fabll.Traits(mul2).get_obj(F.Expressions.Multiply)

    # Really fucked up way to test: rep_app = 8A + 2AB
    expecteds: list[tuple[set[F.Parameters.is_parameter_operatable], float]] = [
        ({rep_A}, 8),
        ({rep_A, rep_B}, 2),
    ]
    for expected_ops, expected_lit in expecteds:
        found = False
        for mul in (mulexp1, mulexp2):
            if (
                next(
                    iter(mul.is_expression.get().get_operand_literals().values())
                ).equals_singleton(expected_lit)
                and set(mul.is_expression.get().get_operand_operatables())
                == expected_ops
            ):
                found = True
                break

        assert found


def test_literal_folding_add_multiplicative_2():
    """
    expr := A + (A * 2) + 10 + (5 * A) + 0 + B
    expr <=! 100 # need predicate for solver
    => 8A + B + 10
    """
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.dl)
    B = E.parameter_op(units=E.U.dl)

    expr = E.add(
        A,
        E.multiply(A, E.lit_op_single(2)),
        E.lit_op_single(10),
        E.multiply(E.lit_op_single(5), A),
        E.lit_op_single(0),
        B,
    )

    E.less_or_equal(expr, E.lit_op_single(100.0), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    rep_add = not_none(
        repr_map.map_forward(expr.as_parameter_operatable.force_get()).maps_to
    )
    a_res = not_none(
        repr_map.map_forward(A.as_parameter_operatable.force_get()).maps_to
    )
    b_res = not_none(
        repr_map.map_forward(B.as_parameter_operatable.force_get()).maps_to
    )

    rep_add_obj = fabll.Traits(rep_add).get_obj(F.Expressions.Add)

    a_ops = [
        op
        for op in a_res.get_operations(F.Expressions.Multiply)
        if any(
            lit
            for lit in op.is_expression.get().get_operand_literals().values()
            if lit.equals_singleton(8)
        )
    ]
    assert len(a_ops) == 1
    mul = next(iter(a_ops))
    add_ops = rep_add_obj.is_expression.get().get_operand_operatables()
    add_ops_lits = rep_add_obj.is_expression.get().get_operand_literals()
    assert len(add_ops_lits) == 1 and next(
        iter(add_ops_lits.values())
    ).equals_singleton(10)
    assert add_ops == {b_res, mul.is_parameter_operatable.get()}


def test_transitive_subset():
    E = BoundExpressions()

    # TODO: Constrain to real number domain
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_subset(A, B, assert_=True)
    E.is_subset(B, C, assert_=True)

    context = F.Parameters.ReprContext()
    for p in (A, B, C):
        p.as_parameter_operatable.force_get().compact_repr(context)

    E.is_subset(C, E.lit_op_range((0, 10)), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g, print_context=context).data.mutation_map
    assert _extract_and_check(A, repr_map, E.lit_op_range((0, 10)), allow_subset=True)


def test_nested_additions():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()
    D = E.parameter_op()

    E.is_subset(A, E.lit_op_single(1), assert_=True)
    E.is_subset(B, E.lit_op_single(1), assert_=True)
    E.is_(C, E.add(A, B), assert_=True)
    E.is_(D, E.add(C, A), assert_=True)

    solver = DefaultSolver()
    repr_map = not_none(solver.simplify(E.tg, E.g).data.mutation_map)

    assert _extract_and_check(A, repr_map, 1)
    assert _extract_and_check(B, repr_map, 1)
    assert _extract_and_check(C, repr_map, 2)
    assert _extract_and_check(D, repr_map, 3)


def test_combined_add_and_multiply_with_ranges():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_subset(A, E.lit_op_range_from_center_rel((1, E.U.dl), 0.01), assert_=True)
    E.is_subset(B, E.lit_op_range_from_center_rel((2, E.U.dl), 0.01), assert_=True)
    E.is_(C, E.add(E.multiply(E.lit_op_single(2), A), B), assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(
        C, solver, E.lit_op_range_from_center_rel((4, E.U.dl), 0.01)
    )


def test_voltage_divider_find_v_out_no_division():
    E = BoundExpressions()
    r_top = E.parameter_op()
    r_bottom = E.parameter_op()
    v_in = E.parameter_op()
    v_out = E.parameter_op()

    E.is_subset(v_in, E.lit_op_range((9, 10)), assert_=True)
    E.is_subset(r_top, E.lit_op_range((10, 100)), assert_=True)
    E.is_subset(r_bottom, E.lit_op_range((10, 100)), assert_=True)
    E.is_(
        v_out,
        E.multiply(
            v_in, r_bottom, E.power(E.add(r_top, r_bottom), E.lit_op_single(-1))
        ),
        assert_=True,
    )
    solver = DefaultSolver()

    # dependency problem prevents finding precise solution of [9/11, 100/11]
    # TODO: automatically rearrange expression to match
    # v_out.alias_is(v_in * (1 / (1 + (r_top / r_bottom))))
    assert _extract_and_check(v_out, solver, E.lit_op_range((0.45, 50)))


def test_voltage_divider_find_v_out_with_division():
    E = BoundExpressions()
    r_top = E.parameter_op()
    r_bottom = E.parameter_op()
    v_in = E.parameter_op()
    v_out = E.parameter_op()

    E.is_subset(v_in, E.lit_op_range((9, 10)), assert_=True)
    E.is_subset(r_top, E.lit_op_range((10, 100)), assert_=True)
    E.is_subset(r_bottom, E.lit_op_range((10, 100)), assert_=True)
    E.is_(
        v_out,
        E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)),
        assert_=True,
    )

    solver = DefaultSolver()
    assert _extract_and_check(v_out, solver, E.lit_op_range((0.45, 50)))


def test_voltage_divider_find_v_out_single_variable_occurrences():
    E = BoundExpressions()
    r_top = E.parameter_op()
    r_bottom = E.parameter_op()
    v_in = E.parameter_op()
    v_out = E.parameter_op()

    E.is_subset(v_in, E.lit_op_range((9, 10)), assert_=True)
    E.is_subset(r_top, E.lit_op_range((10, 100)), assert_=True)
    E.is_subset(r_bottom, E.lit_op_range((10, 100)), assert_=True)
    E.is_(
        v_out,
        E.multiply(
            v_in,
            E.divide(
                E.lit_op_single(1), E.add(E.lit_op_single(1), E.divide(r_top, r_bottom))
            ),
        ),
        assert_=True,
    )

    solver = DefaultSolver()
    assert _extract_and_check(v_out, solver, E.lit_op_range((9 / 11, 100 / 11)))


def test_voltage_divider_find_v_in():
    E = BoundExpressions()
    r_top = E.parameter_op()
    r_bottom = E.parameter_op()
    v_in = E.parameter_op()
    v_out = E.parameter_op()

    E.is_subset(v_out, E.lit_op_range((9, 10)), assert_=True)
    E.is_subset(r_top, E.lit_op_range((10, 100)), assert_=True)
    E.is_subset(r_bottom, E.lit_op_range((10, 100)), assert_=True)
    E.is_(
        v_out,
        E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)),
        assert_=True,
    )

    solver = DefaultSolver()

    # TODO: should find [9.9, 100]
    assert _extract_and_check(v_in, solver, E.lit_op_range((1.8, 200)))


def test_voltage_divider_find_resistances():
    E = BoundExpressions()
    r_top = E.parameter_op(units=E.U.Ohm)
    r_bottom = E.parameter_op(units=E.U.Ohm)
    v_in = E.parameter_op(units=E.U.V)
    v_out = E.parameter_op(units=E.U.V)
    r_total = E.parameter_op(units=E.U.Ohm)

    E.is_subset(v_in, E.lit_op_range(((9, E.U.V), (10, E.U.V))), assert_=True)
    E.is_subset(v_out, E.lit_op_range(((0.9, E.U.V), (1, E.U.V))), assert_=True)
    E.is_subset(
        r_total, E.lit_op_range_from_center_rel((100, E.U.Ohm), 0.01), assert_=True
    )
    E.is_(r_total, E.add(r_top, r_bottom), assert_=True)
    E.is_(
        v_out,
        E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)),
        assert_=True,
    )

    solver = DefaultSolver()
    # FIXME: this test looks funky
    assert _extract_and_check(v_out, solver, E.lit_op_range(((0.9, E.U.V), (1, E.U.V))))

    # TODO: specify r_top (with tolerance), finish solving to find r_bottom


def test_voltage_divider_find_r_top(request: pytest.FixtureRequest):
    if request.node.get_closest_marker("slow") is None:
        assert False, "slow"

    E = BoundExpressions()
    r_top = E.parameter_op(units=E.U.Ohm)
    r_bottom = E.parameter_op(units=E.U.Ohm)
    v_in = E.parameter_op(units=E.U.V)
    v_out = E.parameter_op(units=E.U.V)

    E.is_subset(v_in, E.lit_op_range_from_center_rel((10, E.U.V), 0.01), assert_=True)
    E.is_subset(v_out, E.lit_op_range_from_center_rel((1, E.U.V), 0.01), assert_=True)
    E.is_subset(
        r_bottom, E.lit_op_range_from_center_rel((1, E.U.Ohm), 0.01), assert_=True
    )
    E.is_(
        v_out,
        E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)),
        assert_=True,
    )
    # r_top = (v_in * r_bottom) / v_out - r_bottom

    solver = DefaultSolver()
    assert _extract_and_check(
        r_top,
        solver,
        E.lit_op_range(((10 * 0.99**2) / 1.01 - 1.01, (10 * 1.01**2) / 0.99 - 0.99)),
    )


def test_voltage_divider_reject_invalid_r_top():
    E = BoundExpressions()
    r_top = E.parameter_op(units=E.U.Ohm)
    r_bottom = E.parameter_op(units=E.U.Ohm)
    v_in = E.parameter_op(units=E.U.V)
    v_out = E.parameter_op(units=E.U.V)

    E.is_subset(v_in, E.lit_op_range_from_center_rel((10, E.U.V), 0.01), assert_=True)
    E.is_subset(v_out, E.lit_op_range_from_center_rel((1, E.U.V), 0.01), assert_=True)
    E.is_(
        v_out,
        E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)),
        assert_=True,
    )

    E.is_subset(
        r_bottom, E.lit_op_range_from_center_rel((1, E.U.Ohm), 0.01), assert_=True
    )
    E.is_subset(
        r_top, E.lit_op_range_from_center_rel((999, E.U.Ohm), 0.01), assert_=True
    )

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify(E.tg, E.g)


def test_base_unit_switch():
    # TODO this should use mAh not Ah
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.As)
    E.is_subset(A, E.lit_op_range(((0.100, E.U.As), (0.600, E.U.As))), assert_=True)
    E.greater_or_equal(A, E.lit_op_single((0.100, E.U.As)), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    assert _extract_and_check(
        A, repr_map, E.lit_op_range(((0.100, E.U.As), (0.600, E.U.As)))
    )


def test_congruence_filter():
    E = BoundExpressions()

    A = E.bool_parameter_op()
    x = E.is_subset(A, E.lit_bool(True))

    y1 = E.not_(x, assert_=True)
    y2 = E.not_(x, assert_=True)
    assert (
        y1.as_parameter_operatable.force_get()
        .as_expression.force_get()
        .is_congruent_to(
            y2.as_parameter_operatable.force_get().as_expression.force_get(),
            g=E.g,
            tg=E.tg,
        )
    )

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    y1_mut = repr_map.map_forward(y1.as_parameter_operatable.force_get()).maps_to
    y2_mut = repr_map.map_forward(y2.as_parameter_operatable.force_get()).maps_to
    assert y1_mut == y2_mut


def test_inspect_enum_simple():
    E = BoundExpressions()
    A = E.enum_parameter_op(F.LED.Color)

    E.is_subset(A, E.lit_op_enum(F.LED.Color.EMERALD), assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(A, solver, F.LED.Color.EMERALD)


def test_inspect_enum_led():
    E = BoundExpressions()
    led = F.LED.bind_typegraph(tg=E.tg).create_instance(g=E.g)

    E.is_subset(
        led.color.get().can_be_operand.get(),
        E.lit_op_enum(F.LED.Color.EMERALD),
        assert_=True,
    )

    solver = DefaultSolver()
    assert _extract_and_check(
        led.color.get().can_be_operand.get(),
        solver,
        F.LED.Color.EMERALD,
    )


@pytest.mark.usefixtures("setup_project_config")
def test_jlcpcb_pick_resistor():
    E = BoundExpressions()
    resistor = F.Resistor.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    E.is_subset(
        resistor.resistance.get().can_be_operand.get(),
        E.lit_op_range(((10, E.U.Ohm), (100, E.U.Ohm))),
        assert_=True,
    )

    solver = DefaultSolver()
    pick_part_recursively(resistor, solver)

    assert resistor.has_trait(F.Pickable.has_part_picked)
    print(resistor.get_trait(F.Pickable.has_part_picked).get_part())


@pytest.mark.usefixtures("setup_project_config")
def test_jlcpcb_pick_capacitor():
    E = BoundExpressions()
    capacitor = F.Capacitor.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    E.is_subset(
        capacitor.capacitance.get().can_be_operand.get(),
        E.lit_op_range(((100e-9, E.U.Fa), (1e-6, E.U.Fa))),
        assert_=True,
    )
    E.greater_or_equal(
        capacitor.max_voltage.get().can_be_operand.get(),
        E.lit_op_single((50, E.U.V)),
        assert_=True,
    )

    solver = DefaultSolver()
    pick_part_recursively(capacitor, solver)

    assert capacitor.has_trait(F.Pickable.has_part_picked)
    print(capacitor.get_trait(F.Pickable.has_part_picked).get_part())


@pytest.mark.xfail(reason="TODO: add support for leds")
def test_jlcpcb_pick_led():
    E = BoundExpressions()
    led = F.LED.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    E.is_subset(
        led.color.get().can_be_operand.get(),
        E.lit_op_enum(F.LED.Color.EMERALD),
        assert_=True,
    )
    E.greater_or_equal(
        led.diode.get().max_current.get().can_be_operand.get(),
        E.lit_op_single((0.010, E.U.A)),
        assert_=True,
    )

    solver = DefaultSolver()
    pick_part_recursively(led, solver)

    assert led.has_trait(F.Pickable.has_part_picked)
    print(led.get_trait(F.Pickable.has_part_picked).get_part())


@pytest.mark.xfail(reason="TODO: swap for test without PoweredLED")
def test_jlcpcb_pick_powered_led_simple():
    # TODO: add support for powered leds
    assert False
    # E = BoundExpressions()
    # led = F.PoweredLED
    # led.led.color.constrain_subset(fabll.EnumSet(F.LED.Color.EMERALD))
    # led.power.voltage.constrain_subset(lit_op_range(((1.8, E.U.V), (5.5, E.U.V))))
    # led.led.forward_voltage.constrain_subset(lit_op_range(((1, E.U.V), (4, E.U.V))))

    # solver = DefaultSolver()
    # children_mods = led.get_children(
    #     direct_only=False, types=fabll.Node, required_trait=fabll.is_module
    # )

    # pick_part_recursively(led, solver)

    # picked_parts = [mod for mod in children_mods if mod.has_trait(F.has_part_picked)]
    # assert len(picked_parts) == 2
    # print([(p, p.get_trait(F.has_part_picked).get_part()) for p in picked_parts])


@pytest.mark.xfail(reason="TODO: swap for test without PoweredLED")
def test_jlcpcb_pick_powered_led_regression():
    # TODO: add support for powered leds
    assert False
    # E = BoundExpressions()
    # led = F.PoweredLED()
    # led.led.color.constrain_subset(F.LED.Color.RED)
    # led.power.voltage.alias_is((3, E.U.V))
    # led.led.brightness.constrain_subset(
    #     TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value
    # )

    # solver = DefaultSolver()
    # children_mods = led.get_children(
    #     direct_only=False, types=fabll.Node, required_trait=fabll.is_module
    # )

    # pick_part_recursively(led, solver)

    # picked_parts = [mod for mod in children_mods if mod.has_trait(F.has_part_picked)]
    # assert len(picked_parts) == 2
    # for p in picked_parts:
    #     print(p.get_full_name(types=False), p.get_trait(F.has_part_picked).get_part())
    #     print(p.pretty_params(solver))


def test_simple_parameter_isolation():
    E = BoundExpressions()
    op = F.Expressions.Add

    x_op_y = E.lit_op_range_from_center_rel((3, E.U.dl), 0.01)
    y = E.lit_op_range_from_center_rel((1, E.U.dl), 0.01)
    x_expected = E.lit_op_range_from_center_rel((2, E.U.dl), 0.02)

    X = E.parameter_op()
    Y = E.parameter_op()

    add = op.c(X, Y)
    E.is_subset(add, x_op_y, assert_=True)
    E.is_subset(Y, y, assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(X, solver, x_expected)


def test_abstract_lowpass():
    """
    fc = 1 / (2 * math.pi * sqrt(C * Li))
    Li is! {1e-6+/-1%}
    fc is! {1000+/-1%}
    => C is! {6 * 158765796 .. 6 * 410118344}
    """
    E = BoundExpressions()

    class _Lowpass(fabll.Node):
        pass

    lowpass = _Lowpass.bind_typegraph(tg=E.tg).create_instance(g=E.g)

    Li = E.parameter_op(units=E.U.H, attach_to=(lowpass, "Li"))
    C = E.parameter_op(units=E.U.Fa, attach_to=(lowpass, "C"))
    fc = E.parameter_op(units=E.U.Hz, attach_to=(lowpass, "fc"))

    # formula
    E.is_(
        fc,
        E.divide(
            E.lit_op_single(1),
            E.multiply(E.sqrt(E.multiply(C, Li)), E.lit_op_single(2 * math.pi)),
        ),
        assert_=True,
    )

    # input
    E.is_subset(Li, E.lit_op_range_from_center_rel((1e-6, E.U.H), 0.01), assert_=True)
    E.is_subset(fc, E.lit_op_range_from_center_rel((1000, E.U.Hz), 0.01), assert_=True)

    # solve
    solver = DefaultSolver()

    assert _extract_and_check(
        C,
        solver,
        E.lit_op_range(((6.0 * 158765796, E.U.dl), (6.0 * 410118344, E.U.dl))),
    )


def test_param_isolation():
    E = BoundExpressions()
    X = E.parameter_op()
    Y = E.parameter_op()

    E.is_subset(
        E.add(X, Y), E.lit_op_range_from_center_rel((3, E.U.dl), 0.01), assert_=True
    )
    E.is_subset(Y, E.lit_op_range_from_center_rel((1, E.U.dl), 0.01), assert_=True)

    solver = DefaultSolver()

    assert _extract_and_check(
        X, solver, E.lit_op_range_from_center_rel((2, E.U.dl), 0.02)
    )


@pytest.mark.parametrize(
    "op",
    [
        F.Expressions.Add.c,
        F.Expressions.Multiply.c,
        F.Expressions.Subtract.c,
        F.Expressions.Divide.c,
    ],
)
def test_extracted_literal_folding(
    op: Callable[..., F.Parameters.can_be_operand],
):
    """
    op({0..10}, {10..20})
    """
    E = BoundExpressions()
    A = E.parameter_op(domain=F.NumberDomain.Args(negative=True))
    B = E.parameter_op(domain=F.NumberDomain.Args(negative=True))
    C = E.parameter_op(domain=F.NumberDomain.Args(negative=True))

    lit1 = E.lit_op_range((0, 10))
    lit2 = E.lit_op_range((10, 20))
    lito = not_none(
        _exec_pure_literal_expressions(
            E.g,
            E.tg,
            op(lit1, lit2)
            .as_parameter_operatable.force_get()
            .as_expression.force_get(),
        )
    )

    E.is_subset(A, lit1, assert_=True)
    E.is_subset(B, lit2, assert_=True)
    E.is_(op(A, B), C, assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(C, solver, lito)


def test_fold_pow():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    lit = E.numbers().setup_from_min_max(5, 6, unit=E.u.make_dl())
    lit_operand = E.numbers().setup_from_singleton(2, unit=E.u.make_dl())
    lit_op = lit.can_be_operand.get()
    lit_operand_op = lit_operand.can_be_operand.get()

    E.is_subset(A, lit_op, assert_=True)
    E.is_(B, E.power(A, lit_operand_op), assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map

    assert _extract_and_check(
        B,
        repr_map,
        lit.op_pow_intervals(lit_operand),
    )


def test_graph_split():
    E = BoundExpressions()

    class _App(fabll.Node):
        A = F.Parameters.NumericParameter.MakeChild(unit=E.U.dl)
        B = F.Parameters.NumericParameter.MakeChild(unit=E.U.dl)

    app = _App.bind_typegraph(tg=E.tg).create_instance(g=E.g)

    Aop = app.A.get().can_be_operand.get()
    Bop = app.B.get().can_be_operand.get()

    C = E.parameter_op()
    D = E.parameter_op()
    E.is_(Aop, C, assert_=True)
    E.is_(Bop, D, assert_=True)

    context = F.Parameters.ReprContext()
    for p in (Aop, Bop, C, D):
        p.as_parameter_operatable.force_get().compact_repr(context)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g, print_context=context).data.mutation_map

    assert (
        not_none(
            repr_map.map_forward(
                not_none(Aop.as_parameter_operatable.force_get())
            ).maps_to
        ).g
        is not not_none(
            repr_map.map_forward(
                not_none(Bop.as_parameter_operatable.force_get())
            ).maps_to
        ).g
    )


def test_ss_single_into_alias():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_subset(A, E.lit_op_range((5, 10)), assert_=True)
    E.is_subset(B, E.lit_op_single(5), assert_=True)
    _ = E.add(A, B)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map

    assert _extract_and_check(B, repr_map, 5)
    assert _extract_and_check(A, repr_map, E.lit_op_range((5, 10)))


@pytest.mark.parametrize(
    "op, invert",
    [
        (F.Expressions.GreaterOrEqual.c, False),
        (F.Expressions.LessOrEqual.c, True),
        (F.Expressions.Is.c, True),
        (F.Expressions.Is.c, False),
        (F.Expressions.IsSubset.c, True),
        (F.Expressions.IsSubset.c, False),
        (F.Expressions.IsSuperset.c, True),
        (F.Expressions.IsSuperset.c, False),
    ],
)
def test_find_contradiction_by_predicate(
    op: Callable[
        [F.Parameters.can_be_operand, F.Parameters.can_be_operand],
        F.Parameters.can_be_operand,
    ],
    invert: bool,
):
    """
    A > B, A is [0, 10], B is [20, 30], A further uncorrelated B
    -> [0,10] > [20, 30]
    """
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_subset(A, E.lit_op_range((0, 10)), assert_=True)
    E.is_subset(B, E.lit_op_range((20, 30)), assert_=True)

    if invert:
        op(
            B, A
        ).as_parameter_operatable.force_get().as_expression.force_get().as_assertable.force_get().assert_()
    else:
        op(
            A, B
        ).as_parameter_operatable.force_get().as_expression.force_get().as_assertable.force_get().assert_()

    solver = DefaultSolver()

    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_find_contradiction_by_gt():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_subset(A, E.lit_op_range((0, 10)), assert_=True)
    E.is_subset(B, E.lit_op_range((20, 30)), assert_=True)

    E.greater_than(A, B, assert_=True)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify(E.tg, E.g)


def test_can_add_parameters():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_subset(A, E.lit_op_range((10, 100)), assert_=True)
    E.is_subset(B, E.lit_op_range((10, 100)), assert_=True)
    E.is_(C, E.add(A, B), assert_=True)

    solver = DefaultSolver()

    assert _extract_and_check(C, solver, E.lit_op_range((20, 200)))


@pytest.mark.xfail(reason="TODO, already broken before new core")
def test_ss_estimation_ge():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_subset(A, E.lit_op_range((0, 10)), assert_=True)
    E.greater_or_equal(B, A, assert_=True)

    solver = DefaultSolver()
    res = solver.simplify(E.tg, E.g)
    assert _extract_and_check(
        B, res.data.mutation_map, E.lit_op_range((10, math.inf)), allow_subset=True
    )


def test_fold_mul_zero():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_subset(A, E.lit_op_single(0), assert_=True)
    E.is_subset(B, E.lit_op_range((10, 20)), assert_=True)

    E.is_(C, E.multiply(A, B), assert_=True)

    solver = DefaultSolver()

    assert _extract_and_check(C, solver, 0)


def test_fold_or_true():
    """
    A{S|True} v B is! C
    => C{S|True}
    """
    E = BoundExpressions()
    A = E.bool_parameter_op()
    B = E.bool_parameter_op()
    C = E.bool_parameter_op()

    E.is_subset(A, E.lit_bool(True), assert_=True)

    E.is_(E.or_(A, B), C, assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(C, solver, True)


def test_fold_not():
    E = BoundExpressions()
    A = E.bool_parameter_op()
    B = E.bool_parameter_op()

    E.is_subset(A, E.lit_bool(False), assert_=True)
    E.is_(E.not_(A), B, assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(B, solver, True)


def test_fold_ss_transitive():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_subset(C, E.lit_op_range((0, 10)), assert_=True)
    E.is_subset(B, C, assert_=True)
    E.is_subset(A, B, assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(A, solver, E.lit_op_range((0, 10)))


def test_ss_intersect():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_subset(A, E.lit_op_range((0, 15)), assert_=True)
    E.is_subset(B, E.lit_op_range((10, 20)), assert_=True)
    E.is_subset(C, A, assert_=True)
    E.is_subset(C, B, assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(C, solver, E.lit_op_range((10, 15)))


@pytest.mark.parametrize(
    "left_factory, right_factory, expected",
    [
        (
            # uncorrelated range
            lambda E: [E.lit_op_range((0, 10))],
            lambda E: [E.lit_op_range((0, 10))],
            (True, False),
        ),
        (
            # unequal range
            lambda E: [E.lit_op_range((0, 10))],
            lambda E: [E.lit_op_range((10, 20))],
            (False, False),
        ),
        (
            # uncorrelated ranges
            lambda E: [E.add(E.lit_op_range((0, 10)), E.lit_op_range((0, 20)))],
            lambda E: [E.add(E.lit_op_range((0, 10)), E.lit_op_range((0, 20)))],
            (True, False),
        ),
        (
            # commutative uncorrelated ranges
            lambda E: [E.add(E.lit_op_range((0, 10)), E.lit_op_range((0, 20)))],
            lambda E: [E.add(E.lit_op_range((0, 20)), E.lit_op_range((0, 10)))],
            (True, False),
        ),
        (
            # correlated booleans
            lambda E: [E.not_(E.lit_bool(True))],
            lambda E: [E.not_(E.lit_bool(True))],
            (True, True),
        ),
        (
            # correlated nested booleans
            lambda E: [E.not_(E.not_(E.lit_bool(True)))],
            lambda E: [E.not_(E.not_(E.lit_bool(True)))],
            (True, True),
        ),
        (
            lambda E: [E.multiply(E.lit_op_range((0, 10)), E.lit_op_range((0, 10)))],
            lambda E: [E.multiply(E.lit_op_range((0, 10)), E.lit_op_range((0, 10)))],
            (True, False),
        ),
        (
            lambda E: [
                E.multiply(
                    E.lit_op_range((0, math.inf)),
                    E.lit_op_range((0, math.inf)),
                    E.lit_op_range((0, math.inf)),
                )
            ],
            lambda E: [
                E.multiply(
                    E.lit_op_range((0, math.inf)), E.lit_op_range((0, math.inf))
                ),
            ],
            (False, False),
        ),
        (
            lambda E: [
                E.add(E.lit_op_range((0, math.inf)), E.lit_op_range((0, math.inf)))
            ],
            lambda E: [E.add(E.lit_op_range((0, math.inf)))],
            (False, False),
        ),
    ],
)
def test_congruence_lits(
    left_factory: Callable[[BoundExpressions], list[F.Parameters.can_be_operand]],
    right_factory: Callable[[BoundExpressions], list[F.Parameters.can_be_operand]],
    expected: tuple[bool, bool],
):
    E = BoundExpressions()
    left = left_factory(E)
    right = right_factory(E)
    uncorrelated_congruent = F.Expressions.is_expression.are_pos_congruent(
        left, right, g=E.g, tg=E.tg, allow_uncorrelated=True
    )

    correlated_congruent = F.Expressions.is_expression.are_pos_congruent(
        left, right, g=E.g, tg=E.tg, allow_uncorrelated=False
    )

    assert (uncorrelated_congruent, correlated_congruent) == expected


def test_fold_literals():
    E = BoundExpressions()
    A = E.parameter_op()
    E.is_(A, E.add(E.lit_op_range((0, 10)), E.lit_op_range((0, 10))), assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(A, solver, E.lit_op_range((0, 20)))


def test_implication():
    """
    A is [5, 10]
    A ss 5 ->! B ss 100+/-10%
    A ss 10 ->! B ss 500+/-10%
    A ss! 10
    => B ss! 500+/-10%
    """
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_subset(A, E.lit_op_discrete_set(5, 10), assert_=True)

    E.implies(
        E.is_subset(A, E.lit_op_single(5)),
        E.is_subset(B, E.lit_op_range_from_center_rel((100, E.U.dl), 0.1)),
        assert_=True,
    )
    E.implies(
        E.is_subset(A, E.lit_op_single(10)),
        E.is_subset(B, E.lit_op_range_from_center_rel((500, E.U.dl), 0.1)),
        assert_=True,
    )

    E.is_subset(A, E.lit_op_single(10), assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(
        B, solver, E.lit_op_range_from_center_rel((500, E.U.dl), 0.1)
    )


@pytest.mark.parametrize("A_value", [5, 10, 15])
def test_mapping(A_value: int):
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    X = E.lit_op_range_from_center_rel((100, E.U.dl), 0.1).as_literal.force_get()
    Y = E.lit_op_range_from_center_rel((200, E.U.dl), 0.1).as_literal.force_get()
    Z = E.lit_op_range_from_center_rel((300, E.U.dl), 0.1).as_literal.force_get()

    mapping = {5: X, 10: Y, 15: Z}
    mapping_literals = {
        E.lit_op_single(5).as_literal.force_get(): X,
        E.lit_op_single(10).as_literal.force_get(): Y,
        E.lit_op_single(15).as_literal.force_get(): Z,
    }
    F.Expressions.Mapping.from_operands(A, B, mapping=mapping_literals, assert_=True)

    E.is_subset(A, E.lit_op_single(A_value), assert_=True)

    solver = DefaultSolver()
    res = cast(DefaultSolver.SolverState, solver.simplify_for(A, B))
    assert _extract_and_check(A, res.data.mutation_map, A_value)
    assert _extract_and_check(B, res.data.mutation_map, mapping[A_value])


@pytest.mark.parametrize("op", [F.Expressions.Subtract.c, F.Expressions.Add.c])
def test_subtract_zero(op):
    E = BoundExpressions()

    A = E.parameter_op()
    E.is_(A, (op(E.lit_op_single(1), E.lit_op_single(0))), assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(A, solver, 1)


def test_canonical_subtract_zero():
    E = BoundExpressions()

    A = E.parameter_op()
    E.is_(A, (E.multiply(E.lit_op_single(0), E.lit_op_single(-1))), assert_=True)

    B = E.parameter_op()
    E.is_(
        B,
        (
            E.add(
                E.lit_op_single(1), E.multiply(E.lit_op_single(0), E.lit_op_single(-1))
            )
        ),
        assert_=True,
    )

    solver = DefaultSolver()
    res = cast(DefaultSolver.SolverState, solver.simplify_for(A, B))
    assert _extract_and_check(A, res.data.mutation_map, 0)
    assert _extract_and_check(B, res.data.mutation_map, 1)


def test_nested_fold_scalar():
    E = BoundExpressions()

    A = E.parameter_op()
    E.is_(
        A,
        E.add(E.lit_op_single(1), E.multiply(E.lit_op_single(2), E.lit_op_single(3))),
        assert_=True,
    )

    solver = DefaultSolver()
    assert _extract_and_check(A, solver, 7)


def test_regression_lit_mul_fold_powers():
    E = BoundExpressions()
    A = E.parameter_op()
    E.is_(
        A,
        (
            E.multiply(
                E.power(E.lit_op_single(2), E.lit_op_single(-1)),
                E.power(E.lit_op_single(2), E.lit_op_single(0.5)),
            )
        ),
        assert_=True,
    )

    solver = DefaultSolver()
    assert _extract_and_check(A, solver, 2**-0.5)


def test_nested_fold_interval():
    E = BoundExpressions()
    A = E.parameter_op()
    E.is_(
        A,
        (
            E.add(
                E.lit_op_range_from_center_rel((1, E.U.dl), 0.1),
                E.multiply(
                    E.lit_op_range_from_center_rel((2, E.U.dl), 0.1),
                    E.lit_op_range_from_center_rel((3, E.U.dl), 0.1),
                ),
            )
        ),
        assert_=True,
    )

    solver = DefaultSolver()
    assert _extract_and_check(A, solver, E.lit_op_range((5.76, 8.36)))


def test_simplify_non_terminal_manual_test_1():
    """
    Test that non-terminal simplification works
    No assertions, run with
    FBRK_LOG_PICK_SOLVE=y FBRK_SLOG=y and read log
    """
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.V)
    B = E.add(A, A)

    solver = DefaultSolver()
    solver.simplify(E.g, E.tg)
    _ = E.add(B, A)
    E.is_subset(A, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)

    solver.simplify(E.g, E.tg)

    solver.simplify(E.tg, E.g, terminal=True)

    solver.simplify(E.g, E.tg)


def test_simplify_non_terminal_manual_test_2():
    """
    Test that non-terminal simplification works
    No assertions, run with
    FBRK_LOG_PICK_SOLVE=y FBRK_SLOG=y and read log
    """
    E = BoundExpressions()
    context, ps = _create_letters(E, 3, units=E.U.V)
    A, B, C = ps

    INCREASE = (20, E.U.dl)
    TOLERANCE = 5
    increase = E.add(
        E.lit_op_range_from_center_rel(INCREASE, TOLERANCE),
        E.lit_op_single((100, E.U.dl)),
    )
    for p1, p2 in pairwise(ps):
        E.is_subset(
            p2.as_operand.get(), E.multiply(p1.as_operand.get(), increase), assert_=True
        )
        E.is_(
            p1.as_operand.get(), E.divide(p2.as_operand.get(), increase), assert_=True
        )

    solver = DefaultSolver()
    solver.simplify(E.tg, E.g, terminal=False, print_context=context)

    origin = 1, E.lit_op_range(((9, E.U.V), (11, E.U.V)))
    E.is_(ps[origin[0]].as_operand.get(), (origin[1]), assert_=True)
    solver.simplify(E.g, E.tg)

    solver.simplify_for(*[p.as_operand.get() for p in ps])
    for i, p in enumerate(ps):
        # _inc = increase ** (i - origin[0])
        _inc = E.lit_op_single(1)
        _i = i - origin[0]
        for _ in range(abs(_i)):
            if _i > 0:
                E.is_(_inc, E.multiply(_inc, increase), assert_=True)
            else:
                E.is_(_inc, E.divide(_inc, increase), assert_=True)

        p_lit = solver.extract_superset(p.as_parameter.force_get())
        print(f"{p.as_parameter.force_get().compact_repr(context)}, lit:", p_lit)
        print(f"{p_lit.as_operand.get()}, {E.multiply(origin[1], _inc)}")
        assert p_lit.is_subset_of(E.multiply(origin[1], _inc).as_literal.force_get())
        E.is_subset(p.as_operand.get(), p_lit.as_operand.get(), assert_=True)
        solver.simplify(E.g, E.tg)


# XFAIL --------------------------------------------------------------------------------


# extra formula
# C.alias_is(1 / (4 * math.pi**2 * Li * fc**2))
# TODO test with only fc given
@pytest.mark.xfail(reason="Need more powerful expression reordering")  # TODO
def test_abstract_lowpass_ss():
    E = BoundExpressions()
    Li = E.parameter_op(units=E.U.H)
    C = E.parameter_op(units=E.U.Fa)
    fc = E.parameter_op(units=E.U.Hz)

    # formula
    E.is_(
        fc,
        E.divide(
            E.lit_op_single(1),
            E.multiply(E.lit_op_single(2 * math.pi), E.sqrt(E.multiply(C, Li))),
        ),
        assert_=True,
    )

    # input
    Li_const = E.numbers().setup_from_center_rel(1e-6, 0.01, unit=E.u.make_H())
    fc_const = E.numbers().setup_from_center_rel(1000, 0.01, unit=E.u.make_Hz())
    E.is_subset(Li, Li_const.can_be_operand.get(), assert_=True)
    E.is_subset(fc, fc_const.can_be_operand.get(), assert_=True)

    # solve
    solver = DefaultSolver()
    solver.simplify(E.tg, E.g)

    # C_expected = 1 / (4 * math.pi**2 * Li_const * fc_const**2)
    C_expected = (
        E.numbers()
        .setup_from_singleton(1, unit=E.u.make_dl())
        .op_div_intervals(
            E.numbers()
            .setup_from_singleton(4 * math.pi**2, unit=E.u.make_dl())
            .op_mul_intervals(Li_const)
            .op_mul_intervals(
                fc_const.op_pow_intervals(
                    E.numbers().setup_from_singleton(2, unit=E.u.make_dl())
                ),
            ),
        )
    )

    assert _extract_and_check(C, solver, C_expected)


@pytest.mark.xfail(reason="Need more powerful expression reordering")  # TODO
def test_voltage_divider_find_r_bottom():
    E = BoundExpressions()
    r_top = E.parameter_op(units=E.U.Ohm)
    r_bottom = E.parameter_op(units=E.U.Ohm)
    v_in = E.parameter_op(units=E.U.V)
    v_out = E.parameter_op(units=E.U.V)

    # formula
    E.is_(v_out, E.divide(E.multiply(v_in, r_bottom), E.add(r_top, r_bottom)))

    # input
    E.is_subset(v_in, E.lit_op_range_from_center_rel((10, E.U.V), 0.01), assert_=True)
    E.is_subset(v_out, E.lit_op_range_from_center_rel((1, E.U.V), 0.01), assert_=True)
    E.is_subset(r_top, E.lit_op_range_from_center_rel((9, E.U.Ohm), 0.01), assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(
        r_bottom, solver, E.lit_op_range_from_center_rel((1, E.U.Ohm), 0.01)
    )


@pytest.mark.xfail(reason="TODO reenable ge fold")
def test_min_max_single():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    E.is_subset(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)

    p1 = E.parameter_op(units=E.U.V)
    E.is_(p1, E.max(p0), assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(p1, solver, E.lit_op_single((10, E.U.V)))


@pytest.mark.xfail(reason="TODO")
def test_min_max_multi():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    E.is_subset(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)
    p3 = E.parameter_op(units=E.U.V)
    E.is_subset(p3, E.lit_op_range(((4, E.U.V), (15, E.U.V))), assert_=True)

    p1 = E.parameter_op(units=E.U.V)
    E.is_(p1, E.max(p0, p3), assert_=True)

    solver = DefaultSolver()
    assert _extract_and_check(p1, solver, E.lit_op_single((15, E.U.V)))


@pytest.mark.xfail(
    reason="Behaviour not implemented https://github.com/atopile/atopile/issues/615"
)
def test_symmetric_inequality_uncorrelated():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    p1 = E.parameter_op(units=E.U.V)

    E.is_subset(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)
    E.is_subset(p1, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)

    E.greater_or_equal(p0, p1, assert_=True)
    E.less_or_equal(p0, p1, assert_=True)

    # This would only work if p0 is alias p1
    # but we never do implicit alias, because that's very dangerous
    # so this has to throw

    # strategy: if this kind of unequality exists, check if there is an alias
    # and if not, throw

    solver = DefaultSolver()

    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_fold_correlated():
    """
    ```
    A ss! [5, 10], B ss! [10, 15]
    B is A + 5
    B - A | [10, 15] - [5, 10] = [0, 10] BUT SHOULD BE 5
    ```

    A and B correlated, thus B - A should do ss not alias
    """
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    op = E.add, F.Literals.Numbers.op_add_intervals
    op_inv = E.subtract, F.Literals.Numbers.op_subtract_intervals

    lit1 = E.lit_op_range((5, 10))
    lit1_n = fabll.Traits(lit1).get_obj(F.Literals.Numbers)
    lit_operand = E.lit_op_single(5)
    lit_operand_n = fabll.Traits(lit_operand).get_obj(F.Literals.Numbers)
    lit2_n = op[1](lit1_n, lit_operand_n, g=E.g, tg=E.tg)
    lit2 = lit2_n.can_be_operand.get()

    E.is_subset(A, lit1, assert_=True)  # A ss! [5,10]
    E.is_subset(B, lit2, assert_=True)  # B ss! [10,15]
    # correlate A and B
    E.is_(B, op[0](A, lit_operand), assert_=True)  # B is A + 5
    E.is_(C, op_inv[0](B, A), assert_=True)  # C is B - A

    context = F.Parameters.ReprContext()
    for p in (A, B, C):
        p.as_parameter_operatable.force_get().compact_repr(context)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g, print_context=context).data.mutation_map

    ss_lit = repr_map.try_extract_superset(
        C.as_parameter_operatable.force_get(), allow_subset=True
    )
    assert ss_lit is not None

    # Test for ss estimation
    assert ss_lit.is_subset_of(op_inv[1](lit2_n, lit1_n, g=E.g, tg=E.tg))
    # C ss [10, 15] - 5 == [5, 10]

    # Test for correct is estimation
    try:
        assert not_none(is_lit).equals_singleton(5)  # C is 5
    except AssertionError:
        pytest.xfail("TODO")


_A: list[
    tuple[
        Callable[[BoundExpressions], Callable[..., F.Parameters.can_be_operand]],
        Callable[
            [BoundExpressions],
            list[F.Parameters.can_be_operand | F.Literals.LiteralValues],
        ],
        Callable[
            [BoundExpressions], F.Parameters.can_be_operand | F.Literals.LiteralValues
        ],
    ]
] = [
    # Add tests
    (lambda E: E.add, lambda E: [], lambda E: 0),
    (lambda E: E.add, lambda E: [1, 2, 3, 4, 5], lambda E: 15),
    # Multiply tests
    (lambda E: E.multiply, lambda E: [1, 2, 3, 4, 5], lambda E: 120),
    (lambda E: E.multiply, lambda E: [], lambda E: 1),
    # Power tests
    (lambda E: E.power, lambda E: [2, 3], lambda E: 8),
    # Round tests
    (lambda E: E.round, lambda E: [2.4], lambda E: 2),
    (
        lambda E: E.round,
        lambda E: [E.lit_op_range((-2.6, 5.3))],
        lambda E: E.lit_op_range((-3, 5)),
    ),
    # Abs tests
    (lambda E: E.abs, lambda E: [-2], lambda E: 2),
    (
        lambda E: E.abs,
        lambda E: [E.lit_op_range((-2, 3))],
        lambda E: E.lit_op_range((0, 3)),
    ),
    # Sin tests
    (lambda E: E.sin, lambda E: [0], lambda E: 0),
    (
        lambda E: E.sin,
        lambda E: [E.lit_op_range((0, 2 * math.pi))],
        lambda E: E.lit_op_range((-1, 1)),
    ),
    # Log tests
    (lambda E: E.log, lambda E: [10], lambda E: math.log(10)),
    (
        lambda E: E.log,
        lambda E: [E.lit_op_range((1, 10))],
        lambda E: E.lit_op_range((math.log(1), math.log(10))),
    ),
    # Or tests
    (lambda E: E.or_, lambda E: [False, False, True], lambda E: True),
    (
        lambda E: E.or_,
        lambda E: [False, E.lit_bool(True, False), True],
        lambda E: True,
    ),
    (lambda E: E.or_, lambda E: [], lambda E: False),
    # Not tests
    (lambda E: E.not_, lambda E: [False], lambda E: True),
    # Intersection tests
    (
        lambda E: E.intersection,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((10, 20))],
        lambda E: E.lit_op_range((10, 10)),
    ),
    # Union tests
    (
        lambda E: E.union,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((10, 20))],
        lambda E: E.lit_op_range((0, 20)),
    ),
    # SymmetricDifference tests
    (
        lambda E: E.symmetric_difference,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((10, 20))],
        lambda E: E.lit_op_range((0, 20)),
    ),
    (
        lambda E: E.symmetric_difference,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((5, 20))],
        lambda E: E.lit_op_ranges((0, 5), (10, 20)),
    ),
    # Is tests
    (
        lambda E: E.is_,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((0, 10))],
        lambda E: True,
    ),
    # GreaterOrEqual tests
    (
        lambda E: E.greater_or_equal,
        lambda E: [E.lit_op_range((10, 20)), E.lit_op_range((0, 10))],
        lambda E: True,
    ),
    (
        lambda E: E.greater_or_equal,
        lambda E: [E.lit_op_range((5, 20)), E.lit_op_range((0, 10))],
        lambda E: E.lit_bool(True, False),
    ),
    # GreaterThan tests
    (
        lambda E: E.greater_than,
        lambda E: [E.lit_op_range((10, 20)), E.lit_op_range((0, 10))],
        lambda E: E.lit_bool(True, False),
    ),
    (
        lambda E: E.greater_than,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((10, 20))],
        lambda E: False,
    ),
    # IsSubset tests
    (
        lambda E: E.is_subset,
        lambda E: [E.lit_op_range((0, 10)), E.lit_op_range((0, 20))],
        lambda E: True,
    ),
]


@pytest.mark.parametrize(
    "op_factory, lits_factory, expected_factory",
    _A,
)
def test_exec_pure_literal_expressions(
    op_factory: Callable[
        [BoundExpressions], Callable[..., F.Parameters.can_be_operand]
    ],
    lits_factory: Callable[
        [BoundExpressions], list[F.Parameters.can_be_operand | F.Literals.LiteralValues]
    ],
    expected_factory: Callable[
        [BoundExpressions], F.Parameters.can_be_operand | F.Literals.LiteralValues
    ],
):
    E = BoundExpressions()
    from faebryk.core.solver.symbolic.pure_literal import (
        exec_pure_literal_expression,
    )

    op = op_factory(E)
    lits = lits_factory(E)
    expected = expected_factory(E)

    lits_converted = [
        F.Literals.make_singleton(E.g, E.tg, lit).can_be_operand.get()
        if not isinstance(lit, fabll.Node)
        else lit
        for lit in lits
    ]
    expected_converted = (
        F.Literals.make_singleton(E.g, E.tg, expected).can_be_operand.get()
        if not isinstance(expected, fabll.Node)
        else expected
    ).as_literal.force_get()

    expr = op(*lits_converted)
    expr_e = expr.as_parameter_operatable.force_get().as_expression.force_get()
    assert not_none(exec_pure_literal_expression(E.g, E.tg, expr_e)).equals(
        expected_converted, g=E.g, tg=E.tg
    )

    if op == E.greater_than:
        pytest.xfail("GreaterThan is not supported in solver")

    def _get_param_from_lit(lit: F.Literals.is_literal):
        if fabll.Traits(lit).get_obj_raw().isinstance(F.Literals.Booleans):
            return E.bool_parameter_op()
        else:
            return E.parameter_op(domain=F.NumberDomain.Args(negative=True))

    result = _get_param_from_lit(expected_converted)
    E.is_(result, expr, assert_=True)

    solver = DefaultSolver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    assert _extract_and_check(result, repr_map, expected_converted)


# @pytest.mark.parametrize(
#    "v_in, v_out, total_current",
#    [
#        (
#            lit_op_range(((9.9, E.U.V), (10.1, E.U.V))),
#            lit_op_range(((3.0, E.U.V), (3.2, E.U.V))),
#            lit_op_range(((1, P.mA), (3, P.mA))),
#        ),
#    ],
# )
# def test_solve_voltage_divider_complex(v_in, v_out, total_current):
@pytest.mark.skip(
    reason="TODO: Removed Resistor Voltage Divider, add back with new implementation"
)
def test_solve_voltage_divider_complex():
    pass
    # E = BoundExpressions()
    # v_in, v_out, total_current = (
    #     E.lit_op_range(((9.9, E.U.V), (10.1, E.U.V))),
    #     E.lit_op_range(((3.0, E.U.V), (3.2, E.U.V))),
    #     E.lit_op_range(((1e-3, E.U.A), (3e-3, E.U.A))),
    # )

    # rdiv = F.ResistorVoltageDivider()

    # rdiv.v_in.alias_is(v_in)
    # rdiv.v_out.constrain_subset(v_out)
    # rdiv.max_current.constrain_subset(total_current)

    # # Solve for r_top
    # print("Solving for r_top")
    # solver = DefaultSolver()
    # solver.update_superset_cache(rdiv)

    # r_top = solver.inspect_get_known_supersets(rdiv.r_top.resistance)
    # assert isinstance(r_top, Quantity_Interval_Disjoint)
    # print(f"r_top: {r_top}")
    # expected_r_top = (v_in - v_out) / total_current
    # print(f"Expected r_top: {expected_r_top}")
    # assert r_top == expected_r_top

    # # Pick a random valid resistor for r_top
    # rand_ = Decimal(random())
    # r_any_nominal = r_top.min_elem + rand_ * (r_top.max_elem - r_top.min_elem)
    # assert isinstance(r_any_nominal, Quantity)
    # r_any = lit_op_range_from_center_rel(r_any_nominal, 0.01)
    # rdiv.r_top.resistance.alias_is(r_any)
    # print(f"Set r_top to {r_any}")

    # # Solve for r_bottom
    # solver.update_superset_cache(rdiv)
    # r_bottom = solver.inspect_get_known_supersets(rdiv.r_bottom.resistance)
    # assert isinstance(r_bottom, Quantity_Interval_Disjoint)
    # print(f"r_bottom: {r_bottom}")
    # expected_r_bottom_1 = (v_in / total_current) - r_any
    # expected_r_bottom_2 = v_out / total_current
    # expected_r_bottom_3 = v_out * r_any / (v_in - v_out)
    # print(f"Expected r_bottom subset by voltage: {expected_r_bottom_1}")
    # print(f"Expected r_bottom subset by current: {expected_r_bottom_2}")
    # print(f"Expected r_bottom subset by voltage and current: {expected_r_bottom_3}")
    # assert r_bottom.is_subset_of(expected_r_bottom_1)
    # assert r_bottom.is_subset_of(expected_r_bottom_2)
    # assert r_bottom.is_subset_of(expected_r_bottom_3)
    # # print results
    # res_total_current = v_in / (r_any + r_bottom)
    # # res_v_out = v_in * r_bottom / (r_any + r_bottom)
    # res_v_out = v_in / (1 + r_any / r_bottom)
    # solver_total_current = solver.inspect_get_known_supersets(rdiv.max_current)
    # solver_v_out = solver.inspect_get_known_supersets(rdiv.v_out)
    # print(f"Resulting current {res_total_current} ss! {total_current}")
    # print(f"Solver thinks current is {solver_total_current}")
    # print(f"Resulting v_out {res_v_out} ss! {v_out}")
    # print(f"Solver thinks v_out is {solver_v_out}")

    # # check valid result
    # assert res_total_current.is_subset_of(total_current)
    # if not res_v_out.is_subset_of(v_out) and res_v_out.is_subset_of(
    #     v_out * lit_op_range_from_center_rel(1, 0.05)
    # ):
    #     pytest.xfail("Slightly inaccurate, need more symbolic correlation")

    # assert res_v_out.is_subset_of(v_out)

    # # check solver knowing result
    # assert solver_v_out == res_v_out
    # assert solver_total_current == res_total_current


class TestSubsumptionDetection:
    """
    Test subsumption detection for predicates.

    Subsumption means: if predicate A is true, predicate B is automatically true.
    A "subsumes" B, making B redundant.

    Same-type subsumptions:
    - IsSubset: X ⊆ [0,10] subsumes X ⊆ [0,20] (tighter range)
    - GreaterThan: X > 20 subsumes X > 10 (tighter lower bound)
    - GreaterOrEqual: X >= 20 subsumes X >= 10 (tighter lower bound)

    Cross-type subsumptions:
    - Is → IsSubset: X is 5 subsumes X ⊆ [0,10] when 5 ∈ [0,10]
    - Is → GreaterThan: X is 5 subsumes X > 3 when 5 > 3
    - IsSubset → GreaterThan: X ⊆ [10,20] subsumes X > 5 when min >= 5
    """

    PRED_FACTORIES = {
        "IsSubset": F.Expressions.IsSubset,
        "Is": F.Expressions.Is,
        "GreaterThan": F.Expressions.GreaterThan,
        "GreaterOrEqual": F.Expressions.GreaterOrEqual,
    }

    @staticmethod
    def _run_in_mutator(E, callback, force_copy=True):
        """Run callback within a mutator context, returning its result."""
        from faebryk.core.solver.algorithm import algorithm
        from faebryk.core.solver.mutator import MutationMap, Mutator

        mut_map = MutationMap.bootstrap(tg=E.tg, g=E.g)
        result = None

        @algorithm("test", force_copy=force_copy)
        def test_algo(mutator: Mutator):
            nonlocal result
            result = callback(mutator)

        Mutator(mutation_map=mut_map, algo=test_algo, iteration=0, terminal=True).run()
        return result

    @staticmethod
    def _make_pred(E, pred_spec, operand, assert_=True):
        pred_type, value = pred_spec
        match pred_type:
            case "IsSubset":
                return E.is_subset(operand, E.lit_op_range(value), assert_=assert_)
            case "Is":
                return E.is_(operand, E.lit_op_single(value), assert_=assert_)
            case "GreaterThan":
                return F.Expressions.GreaterThan.from_operands(
                    operand, E.lit_op_single(value), g=E.g, tg=E.tg, assert_=assert_
                )
            case "GreaterOrEqual":
                return F.Expressions.GreaterOrEqual.from_operands(
                    operand, E.lit_op_single(value), g=E.g, tg=E.tg, assert_=assert_
                )
            case _:
                raise ValueError(f"Unknown predicate type: {pred_type}")

    @staticmethod
    def _make_operands(E, pred_spec, operand):
        """Create operands list for find_subsuming_expression."""
        pred_type, value = pred_spec
        literal = (
            E.lit_op_range(value) if pred_type == "IsSubset" else E.lit_op_single(value)
        )
        return [operand, literal]

    @pytest.mark.parametrize(
        "existing_pred, new_pred, expect_subsumed",
        [
            # Same-type: IsSubset with Numbers
            pytest.param(
                ("IsSubset", (0, 10)),
                ("IsSubset", (0, 20)),
                True,
                id="ss_subsumes_ss_positive_tighter_range",
            ),
            pytest.param(
                ("IsSubset", (0, 20)),
                ("IsSubset", (0, 10)),
                False,
                id="ss_subsumes_ss_negative_looser_range",
            ),
            pytest.param(
                ("IsSubset", (5, 15)),
                ("IsSubset", (0, 20)),
                True,
                id="ss_subsumes_ss_positive_inner_range",
            ),
            pytest.param(
                ("IsSubset", (0, 10)),
                ("IsSubset", (5, 15)),
                False,
                id="ss_subsumes_ss_negative_partial_overlap",
            ),
            # Same-type: GreaterThan
            pytest.param(
                ("GreaterThan", 20),
                ("GreaterThan", 10),
                True,
                id="gt_subsumes_gt_positive_higher_bound",
            ),
            pytest.param(
                ("GreaterThan", 10),
                ("GreaterThan", 20),
                False,
                id="gt_subsumes_gt_negative_lower_bound",
            ),
            # Same-type: GreaterOrEqual
            pytest.param(
                ("GreaterOrEqual", 20),
                ("GreaterOrEqual", 10),
                True,
                id="ge_subsumes_ge_positive_higher_bound",
            ),
            pytest.param(
                ("GreaterOrEqual", 10),
                ("GreaterOrEqual", 20),
                False,
                id="ge_subsumes_ge_negative_lower_bound",
            ),
            # Cross-type: Is → IsSubset
            pytest.param(
                ("Is", 5),
                ("IsSubset", (0, 10)),
                True,
                id="is_subsumes_ss_positive_value_in_range",
            ),
            pytest.param(
                ("Is", 15),
                ("IsSubset", (0, 10)),
                False,
                id="is_subsumes_ss_negative_value_outside_range",
            ),
            # Cross-type: Is → GreaterThan
            pytest.param(
                ("Is", 10),
                ("GreaterThan", 5),
                True,
                id="is_subsumes_gt_positive_value_above_bound",
            ),
            pytest.param(
                ("Is", 5),
                ("GreaterThan", 10),
                False,
                id="is_subsumes_gt_negative_value_below_bound",
            ),
            # Cross-type: Is → GreaterOrEqual
            pytest.param(
                ("Is", 10),
                ("GreaterOrEqual", 10),
                True,
                id="is_subsumes_ge_positive_value_equal_bound",
            ),
            pytest.param(
                ("Is", 5),
                ("GreaterOrEqual", 10),
                False,
                id="is_subsumes_ge_negative_value_below_bound",
            ),
            # Cross-type: IsSubset → GreaterThan
            pytest.param(
                ("IsSubset", (10, 20)),
                ("GreaterThan", 5),
                True,
                id="ss_subsumes_gt_positive_range_min_above_bound",
            ),
            pytest.param(
                ("IsSubset", (0, 20)),
                ("GreaterThan", 5),
                False,
                id="ss_subsumes_gt_negative_range_min_below_bound",
            ),
            # Cross-type: IsSubset → GreaterOrEqual
            pytest.param(
                ("IsSubset", (10, 20)),
                ("GreaterOrEqual", 10),
                True,
                id="ss_subsumes_ge_positive_range_min_equal_bound",
            ),
            pytest.param(
                ("IsSubset", (0, 20)),
                ("GreaterOrEqual", 10),
                False,
                id="ss_subsumes_ge_negative_range_min_below_bound",
            ),
            # Cross-type: GreaterThan → GreaterOrEqual
            pytest.param(
                ("GreaterThan", 10),
                ("GreaterOrEqual", 10),
                True,
                id="gt_subsumes_ge_positive_same_bound",
            ),
            pytest.param(
                ("GreaterThan", 10),
                ("GreaterOrEqual", 15),
                False,
                id="gt_subsumes_ge_negative_higher_bound",
            ),
            # Cross-type: GreaterOrEqual → GreaterThan
            pytest.param(
                ("GreaterOrEqual", 20),
                ("GreaterThan", 10),
                True,
                id="ge_subsumes_gt_positive_higher_bound",
            ),
            pytest.param(
                ("GreaterOrEqual", 10),
                ("GreaterThan", 10),
                False,
                id="ge_subsumes_gt_negative_equal_bound",
            ),
        ],
    )
    def test_subsumption_detection(self, existing_pred, new_pred, expect_subsumed):
        E = BoundExpressions()
        X = E.parameter_op()
        self._make_pred(E, existing_pred, X, assert_=True)

        new_type, _ = new_pred
        new_operands = self._make_operands(E, new_pred, X)
        result = self._run_in_mutator(
            E,
            lambda m: m.find_subsuming_expression(
                self.PRED_FACTORIES[new_type], new_operands
            ),
        )

        assert result is not None if expect_subsumed else result is None

    @pytest.mark.parametrize(
        "existing_pred, new_pred, same_param, assert_existing",
        [
            # Different parameter - should never match
            pytest.param(
                ("IsSubset", (0, 10)),
                ("IsSubset", (0, 20)),
                False,
                True,
                id="different_param_ss",
            ),
            pytest.param(
                ("GreaterThan", 20),
                ("GreaterThan", 10),
                False,
                True,
                id="different_param_gt",
            ),
            # Non-predicate (not asserted) - should not be found
            pytest.param(
                ("IsSubset", (0, 10)),
                ("IsSubset", (0, 20)),
                True,
                False,
                id="non_predicate_ss",
            ),
            # Disjoint ranges - no subsumption
            pytest.param(
                ("IsSubset", (0, 10)),
                ("IsSubset", (20, 30)),
                True,
                True,
                id="disjoint_ranges",
            ),
        ],
    )
    def test_false_positives(
        self, existing_pred, new_pred, same_param, assert_existing
    ):
        E = BoundExpressions()
        X = E.parameter_op()
        Y = E.parameter_op() if not same_param else X

        self._make_pred(E, existing_pred, X, assert_=assert_existing)
        new_type = new_pred[0]
        new_operands = self._make_operands(E, new_pred, Y)
        result = self._run_in_mutator(
            E,
            lambda m: m.find_subsuming_expression(
                self.PRED_FACTORIES[new_type], new_operands
            ),
        )

        assert result is None, f"Should NOT detect subsumption, but found: {result}"

    def test_terminated_predicate_still_found(self):
        """
        Terminated predicates SHOULD still be found as subsuming.
        Termination means the solver is done processing the predicate,
        but it still constrains the solution space.
        """
        from faebryk.core.solver.mutator import is_terminated

        E = BoundExpressions()
        X = E.parameter_op()
        existing = E.is_subset(X, E.lit_op_range((0, 10)), assert_=True)
        fabll.Traits.create_and_add_instance_to(
            node=fabll.Traits(existing).get_obj_raw(),
            trait=is_terminated,
        )
        new_operands = [X, E.lit_op_range((0, 20))]
        result = self._run_in_mutator(
            E,
            lambda m: m.find_subsuming_expression(F.Expressions.IsSubset, new_operands),
        )
        assert result is not None

    def test_finds_correct_among_multiple(self):
        E = BoundExpressions()
        X = E.parameter_op()
        Y = E.parameter_op()

        E.is_subset(Y, E.lit_op_range((0, 5)), assert_=True)  # wrong param
        E.is_subset(X, E.lit_op_range((50, 60)), assert_=True)  # disjoint
        E.is_subset(X, E.lit_op_range((0, 10)), assert_=True)  # subsumes

        new_operands = [X, E.lit_op_range((0, 20))]
        result = self._run_in_mutator(
            E,
            lambda m: m.find_subsuming_expression(F.Expressions.IsSubset, new_operands),
        )
        assert result is not None

    def test_finds_predicate_created_during_algo(self):
        E = BoundExpressions()
        X = E.parameter_op()
        lit_tight = E.lit_op_range((0, 10))
        lit_loose = E.lit_op_range((0, 20))

        def create_and_find(mutator):
            # Create a predicate during the algorithm
            mutator.create_expression(
                F.Expressions.IsSubset, X, lit_tight, assert_=True
            )
            # Now try to find subsumption for a looser range
            return mutator.find_subsuming_expression(
                F.Expressions.IsSubset, [X, lit_loose]
            )

        result = self._run_in_mutator(E, create_and_find, force_copy=False)
        assert result is not None

    def test_or_subsumption_subset_operands(self):
        """Or(A, B) subsumes Or(A, B, C) - smaller Or is tighter."""
        E = BoundExpressions()
        X = E.parameter_op()

        # Create predicates A, B, C (as can_be_operand)
        pred_a = E.is_subset(X, E.lit_op_range((0, 10)), assert_=False)
        pred_b = E.is_subset(X, E.lit_op_range((20, 30)), assert_=False)
        pred_c = E.is_subset(X, E.lit_op_range((40, 50)), assert_=False)

        # Create Or(A, B) as existing predicate
        F.Expressions.Or.from_operands(pred_a, pred_b, g=E.g, tg=E.tg, assert_=True)

        # Try to find subsumption for Or(A, B, C)
        new_operands = [pred_a, pred_b, pred_c]
        result = self._run_in_mutator(
            E, lambda m: m.find_subsuming_expression(F.Expressions.Or, new_operands)
        )
        assert result is not None

    def test_or_subsumption_same_operands(self):
        """Or(A, B) subsumes Or(A, B) - same operands."""
        E = BoundExpressions()
        X = E.parameter_op()

        pred_a = E.is_subset(X, E.lit_op_range((0, 10)), assert_=False)
        pred_b = E.is_subset(X, E.lit_op_range((20, 30)), assert_=False)

        F.Expressions.Or.from_operands(pred_a, pred_b, g=E.g, tg=E.tg, assert_=True)

        new_operands = [pred_a, pred_b]
        result = self._run_in_mutator(
            E, lambda m: m.find_subsuming_expression(F.Expressions.Or, new_operands)
        )
        assert result is not None

    def test_or_subsumption_negative_superset(self):
        """Or(A, B, C) does NOT subsume Or(A, B) - larger Or is looser."""
        E = BoundExpressions()
        X = E.parameter_op()

        pred_a = E.is_subset(X, E.lit_op_range((0, 10)), assert_=False)
        pred_b = E.is_subset(X, E.lit_op_range((20, 30)), assert_=False)
        pred_c = E.is_subset(X, E.lit_op_range((40, 50)), assert_=False)

        # Create Or(A, B, C) as existing predicate
        F.Expressions.Or.from_operands(
            pred_a, pred_b, pred_c, g=E.g, tg=E.tg, assert_=True
        )

        # Try to find subsumption for Or(A, B)
        new_operands = [pred_a, pred_b]
        result = self._run_in_mutator(
            E, lambda m: m.find_subsuming_expression(F.Expressions.Or, new_operands)
        )
        assert result is None

    def test_or_subsumption_negative_different_operands(self):
        """Or(A, B) does NOT subsume Or(A, C) - different operands."""
        E = BoundExpressions()
        X = E.parameter_op()

        pred_a = E.is_subset(X, E.lit_op_range((0, 10)), assert_=False)
        pred_b = E.is_subset(X, E.lit_op_range((20, 30)), assert_=False)
        pred_c = E.is_subset(X, E.lit_op_range((40, 50)), assert_=False)

        F.Expressions.Or.from_operands(pred_a, pred_b, g=E.g, tg=E.tg, assert_=True)

        new_operands = [pred_a, pred_c]
        result = self._run_in_mutator(
            E, lambda m: m.find_subsuming_expression(F.Expressions.Or, new_operands)
        )
        assert result is None

    def test_subsumption_check_e2e(self):
        solver = DefaultSolver()
        E = BoundExpressions()

        class _App(fabll.Node):
            param = F.Parameters.NumericParameter.MakeChild(unit=E.U.V)

        app = _App.bind_typegraph(tg=E.tg).create_instance(g=E.g)
        A = app.param.get().can_be_operand.get()

        # Create tighter constraint first: X ⊆ [0, 10]
        tight = E.is_subset(A, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)

        # Create looser constraint: X ⊆ [0, 20]
        loose = E.is_subset(A, E.lit_op_range(((0, E.U.V), (20, E.U.V))), assert_=True)

        repr_map = solver.simplify(E.tg, E.g).data.mutation_map

        tight_mapped = repr_map.map_forward(tight.as_parameter_operatable.force_get())
        loose_mapped = repr_map.map_forward(loose.as_parameter_operatable.force_get())

        assert tight_mapped is not None
        assert loose_mapped is not None
        assert tight_mapped.maps_to is not None
        assert loose_mapped.maps_to is not None
        assert tight_mapped.maps_to.is_same(loose_mapped.maps_to)


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()

    # typer.run(test_simplify)
    # typer.run(
    #    lambda: test_super_simple_literal_folding(F.Expressions.Add.c, (5, 10), 15)
    # )
    typer.run(test_subset_is)
