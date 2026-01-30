# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
import math
import string
from itertools import pairwise
from typing import Callable, cast

import pytest

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.mutator import MutationMap
from faebryk.core.solver.solver import Solver
from faebryk.core.solver.symbolic.pure_literal import exec_pure_literal_expression
from faebryk.core.solver.utils import Contradiction
from faebryk.libs.picker.picker import pick_parts_recursively
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
) -> list[F.Parameters.is_parameter_operatable]:
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

    def generate_letter():
        yield from string.ascii_uppercase

    for letter, p in zip(generate_letter(), app.params):
        p.get().is_parameter.get().set_name(letter)

    params = [p.get().is_parameter_operatable.get() for p in app.params]

    return params


def _extract(
    op: F.Parameters.can_be_operand,
    res: MutationMap | Solver,
    domain_default: bool = False,
) -> F.Literals.is_literal:
    if not isinstance(res, MutationMap):
        assert domain_default
        op_po = op.as_parameter_operatable.force_get()
        if e := op_po.as_expression.try_get():
            p = e.create_representative()
        else:
            p = op_po.as_parameter.force_get()
        return res.simplify_and_extract_superset(p)
    return not_none(
        res.try_extract_superset(
            op.as_parameter_operatable.force_get(),
            domain_default=domain_default,
        )
    )


def _extract_and_check(
    op: F.Parameters.can_be_operand,
    res: MutationMap | Solver,
    expected: F.Parameters.can_be_operand
    | F.Literals.LiteralValues
    | F.Literals.LiteralNodes
    | F.Literals.is_literal,
    domain_default: bool = True,
) -> bool:
    extracted = _extract(op, res, domain_default=domain_default)
    if isinstance(expected, F.Literals.is_literal):
        expected = expected.as_operand.get()
    if isinstance(expected, F.Literals.LiteralNodes):
        expected = expected.can_be_operand.get()
    if not isinstance(expected, F.Parameters.can_be_operand):
        matches = extracted.op_setic_equals_singleton(expected)
        if not matches:
            print(
                f"Expected {expected}"
                f" but got {extracted.pretty_str()}"
                f"\nfor op: {op.as_parameter_operatable.force_get().compact_repr()}"
            )
        return matches

    matches = extracted.op_setic_equals(expected.as_literal.force_get())
    if not matches:
        print(
            f"Expected {expected.as_literal.force_get().pretty_str()}"
            f" but got {extracted.pretty_str()}"
            f"\nfor op: {op.pretty()}"
        )
    return matches


def _extract_numbers(
    solver: Solver, po: F.Parameters.is_parameter_operatable
) -> F.Literals.Numbers:
    return (
        solver.extract_superset(po.as_parameter.force_get())
        .switch_cast()
        .cast(F.Literals.Numbers)
    )


def test_solve_phase_one():
    solver = Solver()
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

    solver = Solver()
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
    assert lit.op_setic_equals(
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

    solver = Solver()
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
    solver = Solver()

    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_shortcircuit_logic_or():
    """
    E1 := Or(*App.p[0:3], True)
    E2 := Or(E1, E1)
    E2 -> True
    """
    E = BoundExpressions()

    class _App(fabll.Node):
        p = [F.Parameters.BooleanParameter.MakeChild() for _ in range(4)]

    app = _App.bind_typegraph(tg=E.tg).create_instance(g=E.g)
    p_ops = [p.get().can_be_operand.get() for p in app.p]

    E1 = E.or_(p_ops[0], E.lit_bool(True))
    for p in p_ops[1:]:
        E1 = E.or_(E1, p)
    E2 = E.or_(E1, E1)
    A = E.bool_parameter_op()
    E.is_(A, E2, assert_=True)

    solver = Solver()
    assert _extract_and_check(A, solver, True)


def test_inequality_to_set():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.dl)
    E.less_than(p0, E.lit_op_single((2, E.U.dl)), assert_=True)
    E.greater_than(p0, E.lit_op_single((1, E.U.dl)), assert_=True)
    solver = Solver()
    assert _extract_and_check(p0, solver, E.lit_op_range((1, 2)))


def test_subset_of_literal():
    E = BoundExpressions()
    p0, p1, p2 = (
        E.parameter_op(
            units=E.U.dl,
            within=fabll.Traits(E.lit_op_range((0, i))).get_obj(F.Literals.Numbers),
        )
        for i in range(3)
    )
    E.is_(p0, p1, assert_=True)
    E.is_(p1, p2, assert_=True)

    solver = Solver()
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

    for p in (A, B, C, D, H):
        p.as_parameter_operatable.force_get().compact_repr()
    solver = Solver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map

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
    assert A_mapped
    assert B_mapped
    assert H_mapped
    assert addition_mapped
    assert addition2_mapped
    assert A_mapped.is_same(B_mapped)

    # C + D and D + C should be unified (commutativity)
    assert addition_mapped.is_same(addition2_mapped)

    # A, B, H should all be unified since they're all aliased to the same Add expression
    assert A_mapped.is_same(H_mapped)


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
    # solver = Solver()
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
    solver = Solver()
    assert _extract_and_check(p0, solver, E.lit_op_range(((5, E.U.V), (9, E.U.V))))


def test_obvious_contradiction_by_literal():
    """
    p0 ss! [0V, 10V]
    p1 ss! [11V, 12V]
    p0 is! p1
    """
    E = BoundExpressions()
    p0, p1 = [E.parameter_op(units=E.U.V) for _ in range(2)]

    E.is_subset(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)
    E.is_subset(p1, E.lit_op_range(((11, E.U.V), (12, E.U.V))), assert_=True)

    E.is_(p0, p1, assert_=True)

    solver = Solver()
    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_subset_superset():
    """
    [0, 15] ss! A
    B ss! [5, 20]
    A is! B
    => Contradiction
    """
    E = BoundExpressions()
    A, B = [E.parameter_op() for _ in range(2)]

    E.is_superset(A, E.lit_op_range((0, 15)), assert_=True)
    E.is_subset(B, E.lit_op_range((5, 20)), assert_=True)
    E.is_(A, B, assert_=True)

    for p in [A, B]:
        p.as_parameter_operatable.force_get().compact_repr()

    solver = Solver()
    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_subset_single_alias():
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.V)

    E.is_subset(A, E.lit_op_single((1, E.U.V)), assert_=True)

    solver = Solver()
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

    for p in params:
        p.as_parameter_operatable.force_get().compact_repr()

    solver = Solver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    A_res = _extract(A, repr_map)
    B_res = _extract(B, repr_map)
    C_res = _extract(C, repr_map)
    assert A_res.op_setic_equals(B_res)
    assert B_res.op_setic_equals(C_res)
    assert A_res.op_setic_equals(C_res)


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

    solver = Solver()
    with pytest.raises(Contradiction, match="Empty superset"):
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

    for p in (A, B, C):
        p.as_parameter_operatable.force_get().compact_repr()

    solver = Solver()
    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_symmetric_inequality_correlated():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    p1 = E.parameter_op(units=E.U.V)

    lit = E.lit_op_range(((0, E.U.V), (10, E.U.V)))
    E.is_subset(p0, lit, assert_=True)
    E.is_(p1, p0, assert_=True)

    E.greater_or_equal(p0, p1, assert_=True)
    E.greater_or_equal(p1, p0, assert_=True)

    solver = Solver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    p0_lit = _extract(p0, repr_map)
    p1_lit = _extract(p1, repr_map)
    assert p0_lit.op_setic_equals(p1_lit)
    assert p0_lit.op_setic_equals(lit.as_literal.force_get())


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

    A = E.parameter_op(units=E.U.dl)
    B = E.parameter_op(units=E.U.dl)
    C = E.parameter_op(units=E.U.dl)

    E.is_subset(A, E.lit_op_single(operands[0]), assert_=True)
    E.is_subset(B, E.lit_op_single(operands[1]), assert_=True)

    expr = expr_type(A, B)
    E.is_(C, expr, assert_=True)

    solver = Solver()
    assert _extract_and_check(C, solver, expected_result)


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
    p = expr.get_sibling_trait(F.Expressions.is_expression).create_representative()

    solver = Solver()

    assert _extract_and_check(p.as_operand.get(), solver, expected)


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

    solver = Solver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map

    rep_add = not_none(
        repr_map.map_forward(expr.as_parameter_operatable.force_get()).maps_to
    )
    rep_A = repr_map.map_forward(A.as_parameter_operatable.force_get()).maps_to
    rep_B = repr_map.map_forward(B.as_parameter_operatable.force_get()).maps_to
    assert rep_A is not None
    assert rep_B is not None

    operands = (
        fabll.Traits(rep_add)
        .get_obj(F.Expressions.Add)
        .is_expression.get()
        .get_operands()
    )
    assert len(operands) == 2, f"{rep_add.compact_repr()}"
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
                ).op_setic_equals_singleton(expected_lit)
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

    solver = Solver()
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
            if lit.op_setic_equals_singleton(8)
        )
    ]
    assert len(a_ops) == 1
    mul = next(iter(a_ops))
    add_ops = rep_add_obj.is_expression.get().get_operand_operatables()
    add_ops_lits = rep_add_obj.is_expression.get().get_operand_literals()
    assert len(add_ops_lits) == 1 and next(
        iter(add_ops_lits.values())
    ).op_setic_equals_singleton(10)
    assert add_ops == {b_res, mul.is_parameter_operatable.get()}


def test_transitive_subset():
    E = BoundExpressions()

    # TODO: Constrain to real number domain
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_subset(A, B, assert_=True)
    E.is_subset(B, C, assert_=True)

    for p in (A, B, C):
        p.as_parameter_operatable.force_get().compact_repr()

    E.is_subset(C, E.lit_op_range((0, 10)), assert_=True)

    solver = Solver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    assert _extract_and_check(A, repr_map, E.lit_op_range((0, 10)))


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

    solver = Solver()
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

    solver = Solver()
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
    solver = Solver()

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

    solver = Solver()
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

    solver = Solver()
    assert _extract_and_check(v_out, solver, E.lit_op_range((9 / 11, 100 / 11)))


@pytest.mark.skip(reason="to_fix")  # FIXME
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

    solver = Solver()

    # TODO: should find [9.9, 100]
    assert _extract_and_check(v_in, solver, E.lit_op_range((1.8, 200)))


def test_voltage_divider_find_resistances():
    E = BoundExpressions()
    r_top = E.parameter_op(units=E.U.Ohm, name="r_top")
    r_bottom = E.parameter_op(units=E.U.Ohm, name="r_bottom")
    v_in = E.parameter_op(units=E.U.V, name="v_in")
    v_out = E.parameter_op(units=E.U.V, name="v_out")
    r_total = E.parameter_op(units=E.U.Ohm, name="r_total")

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

    solver = Solver()
    # FIXME: this test looks funky
    assert _extract_and_check(v_out, solver, E.lit_op_range(((0.9, E.U.V), (1, E.U.V))))

    # TODO: specify r_top (with tolerance), finish solving to find r_bottom


@pytest.mark.skip(reason="to_fix")  # FIXME
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

    solver = Solver()
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

    solver = Solver()
    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_base_unit_switch():
    # TODO this should use mAh not Ah
    E = BoundExpressions()
    A = E.parameter_op(units=E.U.As)
    E.is_subset(A, E.lit_op_range(((0.100, E.U.As), (0.600, E.U.As))), assert_=True)
    E.greater_or_equal(A, E.lit_op_single((0.100, E.U.As)), assert_=True)

    solver = Solver()
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

    solver = Solver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map
    y1_mut = repr_map.map_forward(y1.as_parameter_operatable.force_get()).maps_to
    y2_mut = repr_map.map_forward(y2.as_parameter_operatable.force_get()).maps_to
    assert y1_mut == y2_mut


def test_inspect_enum_simple():
    E = BoundExpressions()
    A = E.enum_parameter_op(F.LED.Color)

    E.is_subset(A, E.lit_op_enum(F.LED.Color.EMERALD), assert_=True)

    solver = Solver()
    assert _extract_and_check(A, solver, F.LED.Color.EMERALD)


def test_inspect_enum_led():
    E = BoundExpressions()
    led = F.LED.bind_typegraph(tg=E.tg).create_instance(g=E.g)

    E.is_subset(
        led.color.get().can_be_operand.get(),
        E.lit_op_enum(F.LED.Color.EMERALD),
        assert_=True,
    )

    solver = Solver()
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

    solver = Solver()
    pick_parts_recursively(resistor, solver)

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

    solver = Solver()
    pick_parts_recursively(capacitor, solver)

    assert capacitor.has_trait(F.Pickable.has_part_picked)
    print(capacitor.get_trait(F.Pickable.has_part_picked).get_part())


@pytest.mark.skip(reason="xfail")  # TODO: add support for leds
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

    solver = Solver()
    pick_parts_recursively(led, solver)

    assert led.has_trait(F.Pickable.has_part_picked)
    print(led.get_trait(F.Pickable.has_part_picked).get_part())


@pytest.mark.skip(reason="xfail")  # TODO: swap for test without PoweredLED
def test_jlcpcb_pick_powered_led_simple():
    # TODO: add support for powered leds
    assert False
    # E = BoundExpressions()
    # led = F.PoweredLED
    # led.led.color.constrain_subset(fabll.EnumSet(F.LED.Color.EMERALD))
    # led.power.voltage.constrain_subset(lit_op_range(((1.8, E.U.V), (5.5, E.U.V))))
    # led.led.forward_voltage.constrain_subset(lit_op_range(((1, E.U.V), (4, E.U.V))))

    # solver = Solver()
    # children_mods = led.get_children(
    #     direct_only=False, types=fabll.Node, required_trait=fabll.is_module
    # )

    # pick_part_recursively(led, solver)

    # picked_parts = [mod for mod in children_mods if mod.has_trait(F.has_part_picked)]
    # assert len(picked_parts) == 2
    # print([(p, p.get_trait(F.has_part_picked).get_part()) for p in picked_parts])


@pytest.mark.skip(reason="xfail")  # TODO: swap for test without PoweredLED
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

    # solver = Solver()
    # children_mods = led.get_children(
    #     direct_only=False, types=fabll.Node, required_trait=fabll.is_module
    # )

    # pick_part_recursively(led, solver)

    # picked_parts = [mod for mod in children_mods if mod.has_trait(F.has_part_picked)]
    # assert len(picked_parts) == 2
    # for p in picked_parts:
    #     print(p.get_full_name(types=False), p.get_trait(F.has_part_picked).get_part())
    #     print(p.pretty_params(solver))


@pytest.mark.skip(reason="to_fix")  # FIXME
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

    solver = Solver()
    assert _extract_and_check(X, solver, x_expected)


@pytest.mark.skip(reason="to_fix")  # FIXME
def test_abstract_lowpass():
    """
    fc = 1 / (2 * math.pi * sqrt(C * Li))
    Li is! {1e-6+/-1%}
    fc is! {1000+/-1%}
    => C is! {0.0253 +/- 3%}

    NOTE: don't trust these calculated values — not human verified
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
    solver = Solver()

    # C = 1 / ((fc * 2*pi)^2 * Li)
    assert _extract_and_check(
        C,
        solver,
        E.lit_op_range_from_center_rel((0.0253, E.U.Fa), 0.03),
    )


@pytest.mark.skip(reason="to_fix")  # FIXME
def test_param_isolation():
    E = BoundExpressions()
    X = E.parameter_op()
    Y = E.parameter_op()

    E.is_subset(
        E.add(X, Y), E.lit_op_range_from_center_rel((3, E.U.dl), 0.01), assert_=True
    )
    E.is_subset(Y, E.lit_op_range_from_center_rel((1, E.U.dl), 0.01), assert_=True)

    solver = Solver()

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
        exec_pure_literal_expression(
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

    solver = Solver()
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

    solver = Solver()
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

    for p in (Aop, Bop, C, D):
        p.as_parameter_operatable.force_get().compact_repr()

    solver = Solver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map

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

    solver = Solver()
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

    solver = Solver()

    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_find_contradiction_by_gt():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_subset(A, E.lit_op_range((0, 10)), assert_=True)
    E.is_subset(B, E.lit_op_range((20, 30)), assert_=True)

    E.greater_than(A, B, assert_=True)

    solver = Solver()
    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_can_add_parameters():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_subset(A, E.lit_op_range((10, 100)), assert_=True)
    E.is_subset(B, E.lit_op_range((10, 100)), assert_=True)
    E.is_(C, E.add(A, B), assert_=True)

    solver = Solver()

    assert _extract_and_check(C, solver, E.lit_op_range((20, 200)))


@pytest.mark.skip(reason="xfail")  # TODO, already broken before new core
def test_ss_estimation_ge():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    E.is_subset(A, E.lit_op_range((0, 10)), assert_=True)
    E.greater_or_equal(B, A, assert_=True)

    solver = Solver()
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

    solver = Solver()

    assert _extract_and_check(C, solver, 0)


def test_fold_or_true():
    """
    A{⊆|True} v B is! C
    => C{⊆|True}
    """
    E = BoundExpressions()
    A = E.bool_parameter_op()
    B = E.bool_parameter_op()
    C = E.bool_parameter_op()

    E.is_subset(A, E.lit_bool(True), assert_=True)

    E.is_(E.or_(A, B), C, assert_=True)

    solver = Solver()
    assert _extract_and_check(C, solver, True)


def test_fold_ss_transitive():
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    E.is_subset(C, E.lit_op_range((0, 10)), assert_=True)
    E.is_subset(B, C, assert_=True)
    E.is_subset(A, B, assert_=True)

    solver = Solver()
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

    solver = Solver()
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

    solver = Solver()
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

    solver = Solver()
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

    solver = Solver()
    res = cast(Solver.SolverState, solver.simplify_for(A, B))
    assert _extract_and_check(A, res.data.mutation_map, A_value)
    assert _extract_and_check(B, res.data.mutation_map, mapping[A_value])


@pytest.mark.parametrize("op", [F.Expressions.Subtract.c, F.Expressions.Add.c])
def test_subtract_zero(op):
    E = BoundExpressions()

    A = E.parameter_op()
    E.is_(A, (op(E.lit_op_single(1), E.lit_op_single(0))), assert_=True)

    solver = Solver()
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

    solver = Solver()
    res = cast(Solver.SolverState, solver.simplify_for(A, B))
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

    solver = Solver()
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

    solver = Solver()
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

    solver = Solver()
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

    solver = Solver()
    solver.simplify(E.g, E.tg, terminal=False)
    _ = E.add(B, A)
    E.is_subset(A, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)

    solver.simplify(E.g, E.tg, terminal=False)

    solver.simplify(E.tg, E.g, terminal=True)


@pytest.mark.skip(reason="to_fix")  # FIXME
def test_simplify_non_terminal_manual_test_2():
    """
    Test that non-terminal simplification works
    No assertions, run with
    FBRK_LOG_PICK_SOLVE=y FBRK_SLOG=y and read log
    """
    E = BoundExpressions()
    ps = _create_letters(E, 3, units=E.U.V)
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

    solver = Solver()
    solver.simplify_for(*[p.as_operand.get() for p in ps], terminal=False)

    origin = 1, E.lit_op_range(((9, E.U.V), (11, E.U.V)))
    E.is_subset(ps[origin[0]].as_operand.get(), (origin[1]), assert_=True)

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
        print(f"{p.as_parameter.force_get().compact_repr()}, lit:", p_lit)
        print(f"{p_lit.as_operand.get()}, {E.multiply(origin[1], _inc)}")
        assert p_lit.op_setic_is_subset_of(
            E.multiply(origin[1], _inc).as_literal.force_get()
        )
        E.is_subset(p.as_operand.get(), p_lit.as_operand.get(), assert_=True)
        solver.simplify(E.g, E.tg)


# XFAIL --------------------------------------------------------------------------------


# extra formula
# C.alias_is(1 / (4 * math.pi**2 * Li * fc**2))
# TODO test with only fc given
@pytest.mark.skip(reason="xfail")  # TODO: Need more powerful expression reordering
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
    solver = Solver()
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


@pytest.mark.skip(reason="xfail")  # TODO: Need more powerful expression reordering
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

    solver = Solver()
    assert _extract_and_check(
        r_bottom, solver, E.lit_op_range_from_center_rel((1, E.U.Ohm), 0.01)
    )


@pytest.mark.skip(reason="xfail")  # TODO: reenable ge fold
def test_min_max_single():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    E.is_subset(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)

    p1 = E.parameter_op(units=E.U.V)
    E.is_(p1, E.max(p0), assert_=True)

    solver = Solver()
    assert _extract_and_check(p1, solver, E.lit_op_single((10, E.U.V)))


@pytest.mark.skip(reason="xfail")  # TODO
def test_min_max_multi():
    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.V)
    E.is_subset(p0, E.lit_op_range(((0, E.U.V), (10, E.U.V))), assert_=True)
    p3 = E.parameter_op(units=E.U.V)
    E.is_subset(p3, E.lit_op_range(((4, E.U.V), (15, E.U.V))), assert_=True)

    p1 = E.parameter_op(units=E.U.V)
    E.is_(p1, E.max(p0, p3), assert_=True)

    solver = Solver()
    assert _extract_and_check(p1, solver, E.lit_op_single((15, E.U.V)))


@pytest.mark.skip(
    reason="xfail"
)  # Behaviour not implemented https://github.com/atopile/atopile/issues/615
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

    solver = Solver()

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

    for p in (A, B, C):
        p.as_parameter_operatable.force_get().compact_repr()

    solver = Solver()
    repr_map = solver.simplify(E.tg, E.g).data.mutation_map

    ss_lit = repr_map.try_extract_superset(C.as_parameter_operatable.force_get())
    assert ss_lit is not None

    # Test for ss estimation
    assert ss_lit.op_setic_is_subset_of(op_inv[1](lit2_n, lit1_n, g=E.g, tg=E.tg))
    # C ss [10, 15] - 5 == [5, 10]

    # Test for correct is estimation
    try:
        assert not_none(ss_lit).op_setic_equals_singleton(5)  # C is 5
    except AssertionError:
        pytest.skip("xfail")


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
    # IsSubset tests
    (
        lambda E: E.is_subset,
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
    logger.info(f"EXPR: {expr_e.compact_repr()}")
    logger.info(f"EXPECTED: {expected_converted.pretty_str()}")
    assert not_none(exec_pure_literal_expression(E.g, E.tg, expr_e)).op_setic_equals(
        expected_converted, g=E.g, tg=E.tg
    )

    if op == E.greater_than:
        pytest.skip("xfail")  # GreaterThan is not supported in solver

    def _get_param_from_lit(lit: F.Literals.is_literal):
        if fabll.Traits(lit).get_obj_raw().isinstance(F.Literals.Booleans):
            return E.bool_parameter_op()
        else:
            return E.parameter_op(domain=F.NumberDomain.Args(negative=True))

    result = _get_param_from_lit(expected_converted)
    E.is_(result, expr, assert_=True)

    solver = Solver()
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
    # solver = Solver()
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


def test_correlated_direct_contradiction():
    """
    Correlated(A, B) and Not(Correlated(A, B)) should contradict.
    """
    E = BoundExpressions()
    p1 = E.parameter_op(units=E.U.Ohm)
    p2 = E.parameter_op(units=E.U.Ohm)

    E.correlated(p1, p2, assert_=True)
    E.not_(E.correlated(p1, p2), assert_=True)

    solver = Solver()
    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_correlated_direct_contradiction_multi():
    """
    Correlated(A, B, C) and Not(Correlated(A, B, C)) should contradict.
    """
    E = BoundExpressions()
    p1 = E.parameter_op(units=E.U.Ohm)
    p2 = E.parameter_op(units=E.U.Ohm)
    p3 = E.parameter_op(units=E.U.Ohm)

    E.correlated(p1, p2, p3, assert_=True)
    E.not_(E.correlated(p1, p2, p3), assert_=True)

    solver = Solver()
    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_correlated_no_contradiction_different_sets():
    """
    Correlated(A, B) and Not(Correlated(A, C)) should NOT contradict.
    These are independent assertions about different parameter pairs.
    """
    E = BoundExpressions()
    p1 = E.parameter_op(units=E.U.Ohm)
    p2 = E.parameter_op(units=E.U.Ohm)
    p3 = E.parameter_op(units=E.U.Ohm)

    E.correlated(p1, p2, assert_=True)
    E.not_(E.correlated(p1, p3), assert_=True)

    solver = Solver()
    solver.simplify(E.tg, E.g)


# Lower estimation tests ---------------------------------------------------------------
def test_lower_estimation_with_uncorrelated_params():
    """
    When parameters are marked as uncorrelated via Not(Correlated(...)),
    lower estimation should propagate subset literals through expressions.

    A ⊇ {4..6}, B ⊇ {2..3}, Not(Correlated(A, B))
    C = A + B
    => C ⊇ {6..9} (propagated from subset literals)
    """
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    # Mark A and B as uncorrelated
    E.not_(E.correlated(A, B), assert_=True)

    # A ⊇ {4..6} means {4..6} is a subset of A (A contains at least {4..6})
    E.is_superset(A, E.lit_op_range((4, 6)), assert_=True)
    # B ⊇ {2..3}
    E.is_superset(B, E.lit_op_range((2, 3)), assert_=True)

    # C = A + B
    C = E.add(A, B)

    solver = Solver()
    result = solver.simplify(E.tg, E.g)

    # The lower estimation should propagate: C ⊇ {4..6} + {2..3} = {6..9}
    # So extract_superset(C) should include at least {6..9}
    extracted = result.data.mutation_map.try_extract_superset(
        C.as_parameter_operatable.force_get()
    )
    assert extracted is not None

    # The extracted superset should be within or equal to {6..9}
    # (it could be wider if upper bounds also apply)
    extracted_nums = fabll.Traits(extracted).get_obj(F.Literals.Numbers)
    min_val = extracted_nums.get_min_value()
    max_val = extracted_nums.get_max_value()

    # Lower bound should be at most 6 (since we're propagating lower bounds)
    assert min_val <= 6, f"Expected min <= 6, got {min_val}"
    # Upper bound should be at least 9
    assert max_val >= 9, f"Expected max >= 9, got {max_val}"


def test_lower_estimation_skipped_when_correlated():
    """
    When parameters are NOT marked as uncorrelated (default is correlated),
    lower estimation should NOT propagate subset literals.

    A ⊇ {4..6}, B ⊇ {2..3} (no uncorrelation marker)
    C = A + B
    => C should NOT have tightened bounds from lower estimation
    """
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    # No uncorrelation marker - default is correlated

    # A ⊇ {4..6}
    E.is_superset(A, E.lit_op_range((4, 6)), assert_=True)
    # B ⊇ {2..3}
    E.is_superset(B, E.lit_op_range((2, 3)), assert_=True)

    # C = A + B
    C = E.add(A, B)

    solver = Solver()
    result = solver.simplify(E.tg, E.g)

    # Without uncorrelation, lower estimation should not apply
    # C should still be unbounded (or only bounded by domain)
    extracted = result.data.mutation_map.try_extract_superset(
        C.as_parameter_operatable.force_get()
    )

    if extracted is not None:
        extracted_nums = fabll.Traits(extracted).get_obj(F.Literals.Numbers)
        min_val = extracted_nums.get_min_value()
        max_val = extracted_nums.get_max_value()

        # If lower estimation was incorrectly applied, we'd have min=6, max=9
        # Without it, bounds should be wider (e.g., unbounded or domain-bounded)
        # Check that bounds are NOT exactly {6..9}
        is_tightly_bounded = abs(min_val - 6) < 0.01 and abs(max_val - 9) < 0.01
        assert not is_tightly_bounded, (
            f"Lower estimation should not apply without uncorrelation marker, "
            f"but got bounds [{min_val}, {max_val}]"
        )


def test_lower_estimation_multiply_uncorrelated():
    """
    Test lower estimation with multiplication of uncorrelated parameters.

    A ⊇ {2..3}, B ⊇ {4..5}, Not(Correlated(A, B))
    C = A * B
    => C ⊇ {8..15}
    """
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()

    # Mark A and B as uncorrelated
    E.not_(E.correlated(A, B), assert_=True)

    # A ⊇ {2..3}
    E.is_superset(A, E.lit_op_range((2, 3)), assert_=True)
    # B ⊇ {4..5}
    E.is_superset(B, E.lit_op_range((4, 5)), assert_=True)

    # C = A * B
    C = E.multiply(A, B)

    solver = Solver()
    result = solver.simplify(E.tg, E.g)

    extracted = result.data.mutation_map.try_extract_superset(
        C.as_parameter_operatable.force_get()
    )
    assert extracted is not None

    extracted_nums = fabll.Traits(extracted).get_obj(F.Literals.Numbers)
    min_val = extracted_nums.get_min_value()
    max_val = extracted_nums.get_max_value()

    # {2..3} * {4..5} = {8..15}
    assert min_val <= 8, f"Expected min <= 8, got {min_val}"
    assert max_val >= 15, f"Expected max >= 15, got {max_val}"


def test_lower_estimation_partial_uncorrelation():
    """
    Test that lower estimation requires ALL parameters to be pairwise uncorrelated.

    A ⊇ {1..2}, B ⊇ {3..4}, C ⊇ {5..6}
    Not(Correlated(A, B)) but NOT Not(Correlated(A, C)) or Not(Correlated(B, C))
    D = A + B + C
    => Lower estimation should NOT apply (not all pairs uncorrelated)
    """
    E = BoundExpressions()
    A = E.parameter_op()
    B = E.parameter_op()
    C = E.parameter_op()

    # Only mark A and B as uncorrelated, not the full set
    E.not_(E.correlated(A, B), assert_=True)

    E.is_superset(A, E.lit_op_range((1, 2)), assert_=True)
    E.is_superset(B, E.lit_op_range((3, 4)), assert_=True)
    E.is_superset(C, E.lit_op_range((5, 6)), assert_=True)

    # D = A + B + C = (A + B) + C
    D = E.add(E.add(A, B), C)

    solver = Solver()
    result = solver.simplify(E.tg, E.g)

    extracted = result.data.mutation_map.try_extract_superset(
        D.as_parameter_operatable.force_get()
    )

    if extracted is not None:
        extracted_nums = fabll.Traits(extracted).get_obj(F.Literals.Numbers)
        min_val = extracted_nums.get_min_value()
        max_val = extracted_nums.get_max_value()

        # If full lower estimation applied, we'd get {9..12}
        # Without full uncorrelation, bounds should be wider
        is_fully_tightened = abs(min_val - 9) < 0.01 and abs(max_val - 12) < 0.01
        # Note: partial uncorrelation might still allow some propagation
        # for the A+B subexpression, but not the full D expression


def test_fold_not_false():
    E = BoundExpressions()
    A = E.bool_parameter_op()
    E.is_subset(A, E.lit_bool(False), assert_=True)

    e1 = E.not_(A)

    solver = Solver()
    assert _extract_and_check(e1, solver, True)


def test_fold_not_contradiction():
    E = BoundExpressions()
    A = E.bool_parameter_op()
    E.is_subset(A, E.lit_bool(True), assert_=True)

    e1 = E.not_(A, assert_=True)

    solver = Solver()
    with pytest.raises(Contradiction):
        _extract_and_check(e1, solver, False)


def test_solver_continuation_after_constraint_addition():
    """
    Test the picking scenario: initial solve -> add constraint -> re-solve.
    This mimics what happens during part picking:
    1. Initial solve with multiple parameters
    2. Pick a part (add IsSuperset constraint to narrow bounds)
    3. Re-solve to propagate narrower bounds to dependent parameters
    """
    import time

    E = BoundExpressions()
    [A, B, C] = _create_letters(E, 3)
    A_op, B_op, C_op = A.as_operand.get(), B.as_operand.get(), C.as_operand.get()

    # Initial design constraint: A in range 1k-10k``
    E.is_subset(A_op, E.lit_op_range((1000, 10000)), assert_=True)

    # B = A * 2 (like a ratio constraint)
    E.is_(B_op, E.multiply(A_op, E.lit_op_single(2)), assert_=True)

    # C = B + 1000
    E.is_(C_op, E.add(B_op, E.lit_op_single(1000)), assert_=True)

    solver = Solver()
    t0 = time.perf_counter()
    solver.simplify(E.g, E.tg, terminal=False, relevant=[A_op, B_op, C_op])
    initial_solve_time = time.perf_counter() - t0

    B_initial = _extract_numbers(solver, B)
    C_initial = _extract_numbers(solver, C)

    # Simulate picking a part: narrow A to [4k, 6k] (like selecting a specific resistor)
    E.is_subset(A_op, E.lit_op_range((4000, 6000)), assert_=True)

    # Re-solve (should be faster)
    t1 = time.perf_counter()
    solver.simplify(E.g, E.tg, terminal=False, relevant=[A_op, B_op, C_op])
    continuation_solve_time = time.perf_counter() - t1

    B_after = _extract_numbers(solver, B)
    C_after = _extract_numbers(solver, C)

    # Should be tighter than initial
    assert B_after.get_min_value() >= B_initial.get_min_value(), "B should be tighter"
    assert B_after.get_max_value() <= B_initial.get_max_value(), "B should be tighter"
    assert C_after.get_min_value() >= C_initial.get_min_value(), "C should be tighter"
    assert C_after.get_max_value() <= C_initial.get_max_value(), "C should be tighter"

    # Timing report
    print("\n=== Solver Continuation Timing Report ===")
    print(f"Initial solve time:      {initial_solve_time * 1000:.2f} ms")
    print(f"Continuation solve time: {continuation_solve_time * 1000:.2f} ms")
    if initial_solve_time > 0:
        speedup = (
            initial_solve_time / continuation_solve_time
            if continuation_solve_time > 0
            else float("inf")
        )
        print(f"Speedup:                 {speedup:.2f}x")
    print("==========================================\n")


def test_solver_continuation_multi_pick_scenario():
    """
    Test a more realistic picking scenario with multiple components.
    Simulates picking 3 components sequentially and verifies constraint propagation.
    """
    import time

    E = BoundExpressions()
    params = _create_letters(E, 5)
    params_ops = [p.as_operand.get() for p in params]

    # Initial constraint: first param in range 1k-100k
    E.is_subset(params_ops[0], E.lit_op_range((1000, 100000)), assert_=True)

    # Chain dependencies: each param = previous * 0.9
    for i in range(len(params_ops) - 1):
        E.is_(
            params_ops[i + 1],
            E.multiply(params_ops[i], E.lit_op_single(0.9)),
            assert_=True,
        )

    solver = Solver()
    timings: list[tuple[str, float]] = []

    t0 = time.perf_counter()
    solver.simplify(E.g, E.tg, terminal=False, relevant=params_ops)
    timings.append(("Initial solve", time.perf_counter() - t0))

    P4_initial = _extract_numbers(solver, params[4])

    # Pick component 0: add constraint to narrow bounds (like picking a part)
    E.is_subset(params_ops[0], E.lit_op_range((50000, 60000)), assert_=True)
    t1 = time.perf_counter()
    solver.simplify(E.g, E.tg, terminal=False, relevant=params_ops)
    timings.append(("After pick 1", time.perf_counter() - t1))

    # Verify tightening
    P4_after1 = _extract_numbers(solver, params[4])
    assert P4_after1.get_max_value() <= P4_initial.get_max_value(), (
        "P4 should be tighter after pick 1"
    )

    # Pick component 2: add another constraint
    E.is_subset(params_ops[2], E.lit_op_range((35000, 45000)), assert_=True)
    t2 = time.perf_counter()
    solver.simplify(E.g, E.tg, terminal=False, relevant=params_ops)
    timings.append(("After pick 2", time.perf_counter() - t2))

    # Pick component 3
    E.is_subset(params_ops[3], E.lit_op_range((30000, 42000)), assert_=True)
    t3 = time.perf_counter()
    solver.simplify(E.g, E.tg, terminal=False, relevant=params_ops)
    timings.append(("After pick 3", time.perf_counter() - t3))

    # Final verification
    P4_final = _extract_numbers(solver, params[4])
    assert P4_final.get_min_value() >= 0, "P4 min should be positive"

    # Timing report
    print("\n=== Multi-Pick Solver Continuation Timing Report ===")
    for name, duration in timings:
        print(f"{name:20s}: {duration * 1000:8.2f} ms")
    if len(timings) >= 2:
        avg_continuation = sum(t for _, t in timings[1:]) / len(timings[1:])
        initial_time = timings[0][1]
        if avg_continuation > 0:
            speedup = initial_time / avg_continuation
            print(f"{'Avg speedup':20s}: {speedup:8.2f}x")
    print("=====================================================\n")


def test_inter_algorithm_relevance_filtering():
    from faebryk.core.solver.algorithm import algorithm
    from faebryk.core.solver.mutator import Mutator

    E = BoundExpressions()

    # Create two independent parameters with constraints
    A, B = _create_letters(E, 2, units=E.U.Ohm)
    A_op, B_op = A.as_operand.get(), B.as_operand.get()
    E.is_subset(A_op, E.lit_op_range(((1, E.U.Ohm), (2, E.U.Ohm))), assert_=True)
    B_constraint = E.is_subset(
        B_op, E.lit_op_range(((3, E.U.Ohm), (4, E.U.Ohm))), assert_=True
    )

    relevant_pos = [B_op, B_constraint]

    # Get all parameter operatables before filtering
    all_pos_before = list(
        fabll.Traits.get_implementors(
            F.Parameters.is_parameter_operatable.bind_typegraph(E.tg), E.g
        )
    )

    @algorithm(name="test")
    def algo(mutator: Mutator):
        pass

    mutator = Mutator(
        MutationMap._with_relevance_set(E.g, E.tg, [B_op], 0),
        algo,
        0,
        False,
    )
    mutator.run()

    all_pos_after = mutator.get_parameter_operatables(include_irrelevant=False)

    for po in all_pos_after:
        for mapped in mutator.mutation_map.map_backward(po):
            assert mapped.as_operand.get() in relevant_pos, (
                f"Expected {mapped.compact_repr()} to be in relevant_pos"
            )

    # Filtered count should be less than initial count
    assert len(all_pos_after) < len(all_pos_before), (
        f"Expected fewer operables after filtering. "
        f"Initial: {len(all_pos_before)}, Filtered: {len(all_pos_after)}"
    )


def test_get_relevant_predicates_skips_non_constraining():
    """
    Test that get_relevant_predicates skips Correlated expressions when
    computing the transitive closure of relevant predicates.

    Correlated expressions indicate statistical correlation, not constraint
    dependency, so they should not create edges in the relevance graph.
    """
    from faebryk.core.solver.utils import MutatorUtils

    E = BoundExpressions()
    A, B, C = _create_letters(E, 3, units=E.U.Ohm)
    A_op, B_op, C_op = A.as_operand.get(), B.as_operand.get(), C.as_operand.get()

    # A and B are correlated (non-constraining)
    E.correlated(A_op, B_op, assert_=True)

    # A has a constraint
    E.is_subset(A_op, E.lit_op_range(((1, E.U.Ohm), (2, E.U.Ohm))), assert_=True)

    # C = A + B (constraining relationship)
    C_expr = E.add(A_op, B_op)
    E.is_(C_op, C_expr, assert_=True)

    # Get relevant predicates starting from A
    relevant_preds = MutatorUtils.get_relevant_predicates(A_op)

    # The Correlated predicate should NOT be in the relevant set
    # because it's non-constraining
    for pred in relevant_preds:
        expr = pred.as_expression.get()
        assert not expr.expr_isinstance(F.Expressions.Correlated), (
            "Correlated should not be in relevant predicates"
        )

    # But the IsSubset and Is predicates should be there
    has_is_subset = any(
        pred.as_expression.get().expr_isinstance(F.Expressions.IsSubset)
        for pred in relevant_preds
    )
    assert has_is_subset, "IsSubset should be in relevant predicates"


def test_relevance_filtering_isolates_independent_subgraphs():
    """
    Test that relevance filtering correctly isolates independent constraint subgraphs.

    When we have two independent constraint systems (A with its constraints,
    B with its constraints), marking only A as relevant should mark B's entire
    subgraph as irrelevant.
    """
    from faebryk.core.solver.algorithm import algorithm
    from faebryk.core.solver.mutator import Mutator, is_irrelevant, is_relevant

    E = BoundExpressions()
    A, B, A2, B2 = _create_letters(E, 4, units=E.U.Ohm)
    A_op, B_op, A2_op, B2_op = (
        A.as_operand.get(),
        B.as_operand.get(),
        A2.as_operand.get(),
        B2.as_operand.get(),
    )

    # Create independent constraint subgraph for A
    E.is_subset(A_op, E.lit_op_range(((1, E.U.Ohm), (2, E.U.Ohm))), assert_=True)
    E.is_(A2_op, E.multiply(A_op, E.lit_op_single((2, E.U.dl))), assert_=True)

    # Create independent constraint subgraph for B
    E.is_subset(B_op, E.lit_op_range(((3, E.U.Ohm), (4, E.U.Ohm))), assert_=True)
    E.is_(B2_op, E.multiply(B_op, E.lit_op_single((3, E.U.dl))), assert_=True)

    @algorithm(name="test")
    def algo(mutator: Mutator):
        pass

    mutator = Mutator(
        MutationMap._with_relevance_set(E.g, E.tg, [A_op], 0),
        algo,
        0,
        False,
    )
    mutator.mark_relevance()

    def _try_get_trait[T: fabll.NodeT](
        po: F.Parameters.is_parameter_operatable, trait_t: type[T]
    ) -> T | None:
        mapped = mutator.mutation_map.map_forward(po).maps_to
        if mapped is None:
            return None

        return mapped.try_get_sibling_trait(trait_t)

    # A should be is_relevant (originally specified)
    assert _try_get_trait(A, is_relevant) is not None, "A should be relevant"
    assert _try_get_trait(A, is_irrelevant) is None, "A should NOT be irrelevant"

    # A2 is transitively connected to A: not is_relevant, but not is_irrelevant either
    assert _try_get_trait(A2, is_relevant) is None, (
        "A2 should NOT be is_relevant (not originally specified)"
    )
    assert _try_get_trait(A2, is_irrelevant) is None, "A2 should NOT be irrelevant"

    # B and B2 should not be in the output graph at all
    assert mutator.mutation_map.map_forward(B).maps_to is None, (
        "B should not be mapped (independent subgraph)"
    )
    assert mutator.mutation_map.map_forward(B2).maps_to is None, (
        "B2 should not be mapped (independent subgraph)"
    )


def test_is_irrelevant_trait_filtering_in_queries():
    """
    Test that the is_irrelevant trait is correctly used to filter operatables
    in query operations.
    """
    from faebryk.core.solver.mutator import is_irrelevant

    E = BoundExpressions()

    # Create parameters
    A = E.parameter_op(units=E.U.Ohm)
    B = E.parameter_op(units=E.U.Ohm)

    # Get parameter operatables
    A_po = A.as_parameter_operatable.force_get()
    B_po = B.as_parameter_operatable.force_get()

    # Mark B as irrelevant
    B_obj = fabll.Traits(B_po).get_obj_raw()
    fabll.Traits.create_and_add_instance_to(B_obj, is_irrelevant)

    # Verify B has the trait
    assert B_po.try_get_sibling_trait(is_irrelevant) is not None, (
        "B should have is_irrelevant trait"
    )

    # Verify A does NOT have the trait
    assert A_po.try_get_sibling_trait(is_irrelevant) is None, (
        "A should NOT have is_irrelevant trait"
    )

    # Query all parameter operatables with is_irrelevant
    all_irrelevant = list(
        fabll.Traits.get_implementor_siblings(
            is_irrelevant.bind_typegraph(E.tg),
            F.Parameters.is_parameter_operatable,
            E.g,
        )
    )

    # B should be in the irrelevant set
    assert B_po in all_irrelevant, "B should be in irrelevant set"

    # A should NOT be in the irrelevant set
    assert A_po not in all_irrelevant, "A should NOT be in irrelevant set"

    # Test filtering: get all operatables excluding irrelevant
    all_pos = list(
        fabll.Traits.get_implementors(
            F.Parameters.is_parameter_operatable.bind_typegraph(E.tg), E.g
        )
    )
    filtered_pos = [
        po for po in all_pos if po.try_get_sibling_trait(is_irrelevant) is None
    ]

    assert A_po in filtered_pos, "A should be in filtered set"
    assert B_po not in filtered_pos, "B should NOT be in filtered set"


def test_is_non_constraining_method():
    """
    Test the is_non_constraining method on is_expression trait.

    Correlated(...) and Not(Correlated(...)) should return True.
    Regular predicates like Is, IsSubset should return False.
    """
    E = BoundExpressions()

    A = E.parameter_op()
    B = E.parameter_op()

    # Create Correlated expression
    corr = E.correlated(A, B)
    corr_expr = corr.as_parameter_operatable.force_get().as_expression.force_get()
    assert corr_expr.is_non_constraining(), "Correlated(...) should be non-constraining"

    # Create Not(Correlated(...)) expression
    not_corr = E.not_(corr, assert_=False)
    not_corr_expr = (
        not_corr.as_parameter_operatable.force_get().as_expression.force_get()
    )
    assert not_corr_expr.is_non_constraining(), (
        "Not(Correlated(...)) should be non-constraining"
    )

    # Create regular IsSubset predicate - should NOT be non-constraining
    is_subset_pred = E.is_subset(A, E.lit_op_range((1, 2)), assert_=True)
    is_subset_expr = (
        is_subset_pred.as_parameter_operatable.force_get().as_expression.force_get()
    )
    assert not is_subset_expr.is_non_constraining(), (
        "IsSubset should NOT be non-constraining"
    )

    # Create Is predicate - should NOT be non-constraining
    is_pred = E.is_(A, B, assert_=True)
    is_pred_expr = is_pred.as_parameter_operatable.force_get().as_expression.force_get()
    assert not is_pred_expr.is_non_constraining(), "Is should NOT be non-constraining"
