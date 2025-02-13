# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from operator import add, mul, sub, truediv
from typing import Any, Iterable

import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import (
    Abs,
    Add,
    And,
    Arithmetic,
    Expression,
    GreaterOrEqual,
    GreaterThan,
    Intersection,
    Is,
    IsSubset,
    IsSuperset,
    LessOrEqual,
    Log,
    Max,
    Multiply,
    Not,
    Or,
    Parameter,
    ParameterOperatable,
    Power,
    Predicate,
    Round,
    Sin,
    Subtract,
    SymmetricDifference,
    Union,
)
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.utils import (
    CanonicalExpression,
    CanonicalLiteral,
    Contradiction,
    ContradictionByLiteral,
)
from faebryk.libs.library import L
from faebryk.libs.library.L import DiscreteSet, Range, RangeWithGaps, Single
from faebryk.libs.picker.lcsc import LCSC_Part
from faebryk.libs.picker.picker import (
    PickerOption,
    pick_module_by_params,
    pick_part_recursively,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval_Disjoint,
    Quantity_Set,
)
from faebryk.libs.sets.sets import BoolSet, EnumSet
from faebryk.libs.units import P, dimensionless, quantity
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


def test_solve_phase_one():
    solver = DefaultSolver()

    def Voltage():
        return L.p_field(units=P.V, within=Range(0 * P.V, 10 * P.kV))

    class App(Module):
        voltage1 = Voltage()
        voltage2 = Voltage()
        voltage3 = Voltage()

    app = App()
    voltage1 = app.voltage1
    voltage2 = app.voltage2
    voltage3 = app.voltage3

    voltage1.alias_is(voltage2)
    voltage3.alias_is(voltage1 + voltage2)

    voltage1.alias_is(Range(1 * P.V, 3 * P.V))
    voltage3.alias_is(Range(2 * P.V, 6 * P.V))

    solver.simplify_symbolically(voltage1.get_graph())


def test_simplify():
    class App(Module):
        ops = L.list_field(
            10,
            lambda: Parameter(
                units=dimensionless, within=Range(0, 1, units=dimensionless)
            ),
        )

    app = App()

    # (((((((((((A + B + 1) + C + 2) * D * 3) * E * 4) * F * 5) * G * (A - A)) + H + 7)
    #  + I + 8) + J + 9) - 3) - 4) < 11
    # => (H + I + J + 17) < 11
    constants: list[ParameterOperatable.NumberLike] = [
        quantity(c, dimensionless) for c in range(0, 10)
    ]
    constants[5] = app.ops[0] - app.ops[0]
    constants[9] = RangeWithGaps(Range(0 * dimensionless, 1 * dimensionless))
    acc = app.ops[0]
    for i, p in enumerate(app.ops[1:3]):
        acc += p + constants[i]
    for i, p in enumerate(app.ops[3:7]):
        acc *= p * constants[i + 3]
    for i, p in enumerate(app.ops[7:]):
        acc += p + constants[i + 7]

    acc = (acc - quantity(3, dimensionless)) - quantity(4, dimensionless)
    assert isinstance(acc, Subtract)
    (acc <= quantity(11, dimensionless)).constrain()

    G = acc.get_graph()
    solver = DefaultSolver()
    solver.simplify_symbolically(G)
    # TODO actually test something


def test_simplify_logic_and():
    class App(Module):
        p = L.list_field(4, lambda: Parameter(domain=L.Domains.BOOL()))

    app = App()
    anded = And(app.p[0], True)
    for p in app.p[1:]:
        anded = anded & p
    anded = anded & anded

    anded.constrain()
    G = anded.get_graph()
    solver = DefaultSolver()
    solver.simplify_symbolically(G)
    # TODO actually test something


def test_shortcircuit_logic_and():
    p0 = Parameter(domain=L.Domains.BOOL())
    expr = p0 & False
    expr.constrain()
    G = expr.get_graph()
    solver = DefaultSolver()

    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(G)


def test_shortcircuit_logic_or():
    class App(Module):
        p = L.list_field(4, lambda: Parameter(domain=L.Domains.BOOL()))

    app = App()
    ored = Or(app.p[0], True)
    for p in app.p[1:]:
        ored = ored | p
    ored = ored | ored

    ored.constrain()
    G = ored.get_graph()
    solver = DefaultSolver()
    repr_map, context = solver.simplify_symbolically(G)
    assert repr_map[ored] == BoolSet(True)


def test_inequality_to_set():
    p0 = Parameter(units=dimensionless)
    p0.constrain_le(2.0)
    p0.constrain_ge(1.0)
    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(p0) == RangeWithGaps((1.0, 2.0))


def test_remove_obvious_tautologies():
    p0, p1, p2 = times(3, Parameter)
    p0.alias_is(p1 + p2)
    p1.constrain_ge(0.0)
    p2.constrain_ge(0.0)
    p2.alias_is(p2)

    G = p0.get_graph()
    solver = DefaultSolver()
    solver.simplify_symbolically(G)
    # TODO actually test something


def test_subset_of_literal():
    p0, p1, p2 = (
        Parameter(units=dimensionless, within=Range(0, i, units=dimensionless))
        for i in range(3)
    )
    p0.alias_is(p1)
    p1.alias_is(p2)

    solver = DefaultSolver()
    for p in (p0, p1, p2):
        assert solver.inspect_get_known_supersets(p) == RangeWithGaps((0.0, 0.0))


def test_alias_classes():
    A, B, C, D, E = (Parameter() for _ in range(5))
    A.alias_is(B)
    addition = C + D
    B.alias_is(addition)
    addition2 = D + C
    E.alias_is(addition2)

    G = A.get_graph()
    context = ParameterOperatable.ReprContext()
    for p in (A, B, C, D, E):
        p.compact_repr(context)
    solver = DefaultSolver()
    solver.simplify_symbolically(G, context)
    # TODO actually test something


def test_solve_realworld():
    app = F.RP2040()
    solver = DefaultSolver()
    solver.simplify_symbolically(app.get_graph())
    # TODO actually test something


def test_solve_realworld_bigger():
    app = F.RP2040_ReferenceDesign()
    F.is_bus_parameter.resolve_bus_parameters(app.get_graph())

    solver = DefaultSolver()
    solver.simplify_symbolically(app.get_graph())
    # TODO actually test something


def test_inspect_known_superranges():
    p0 = Parameter(units=P.V, within=Range(1 * P.V, 10 * P.V))
    p0.alias_is(Range(1 * P.V, 3 * P.V) + Range(4 * P.V, 6 * P.V))
    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(p0) == RangeWithGaps((5 * P.V, 9 * P.V))


def test_obvious_contradiction_by_literal():
    p0 = Parameter(units=P.V)
    p1 = Parameter(units=P.V)

    p0.alias_is(Range(0 * P.V, 10 * P.V))
    p1.alias_is(Range(5 * P.V, 10 * P.V))

    p0.alias_is(p1)

    G = p0.get_graph()
    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(G)


def test_subset_is():
    A, B = params = times(2, lambda: Parameter(domain=L.Domains.Numbers.REAL()))

    A.alias_is(Range(0, 15))
    B.constrain_subset(Range(5, 20))
    A.alias_is(B)

    context = ParameterOperatable.ReprContext()
    for p in params:
        p.compact_repr(context)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(A.get_graph())


def test_subset_is_expr():
    A, B, C = params = times(3, lambda: Parameter(domain=L.Domains.Numbers.REAL()))

    context = ParameterOperatable.ReprContext()
    for p in params:
        p.compact_repr(context)

    E = A + B
    C.alias_is(Range(0, 15))
    E.constrain_subset(Range(5, 20))

    C.alias_is(E)

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(A.get_graph(), context)


def test_subset_single_alias():
    A = Parameter(units=P.V)
    A.constrain_subset(Single(1 * P.V))

    solver = DefaultSolver()
    repr_map, context = solver.simplify_symbolically(A.get_graph())
    assert repr_map[A] == Single(1 * P.V)


def test_very_simple_alias_class():
    A, B, C = params = times(3, lambda: Parameter(units=P.V))
    A.alias_is(B)
    B.alias_is(C)

    context = ParameterOperatable.ReprContext()
    for p in params:
        p.compact_repr(context)

    solver = DefaultSolver()
    repr_map, context = solver.simplify_symbolically(A.get_graph(), context)
    r2_map = repr_map.repr_map
    assert r2_map[A] == r2_map[B] == r2_map[C]


def test_domain():
    p0 = Parameter(units=P.V, within=Range(0 * P.V, 10 * P.V))
    p0.alias_is(Range(15 * P.V, 20 * P.V))

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(p0.get_graph())


def test_less_obvious_contradiction_by_literal():
    A = Parameter(units=P.V)
    B = Parameter(units=P.V)
    C = Parameter(units=P.V)

    A.alias_is(Range(0.0 * P.V, 10.0 * P.V))
    B.alias_is(Range(5.0 * P.V, 10.0 * P.V))
    C.alias_is(A + B)
    C.alias_is(Range(0.0 * P.V, 15.0 * P.V))

    print_context = ParameterOperatable.ReprContext()
    for p in (A, B, C):
        p.compact_repr(print_context)

    G = A.get_graph()
    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        repr_map, context = solver.simplify_symbolically(G, print_context)


def test_symmetric_inequality_correlated():
    p0 = Parameter(units=P.V)
    p1 = Parameter(units=P.V)

    p0.alias_is(Range(0 * P.V, 10 * P.V))
    p1.alias_is(p0)

    (p0 >= p1).constrain()
    (p0 <= p1).constrain()

    G = p0.get_graph()
    solver = DefaultSolver()
    repr_map, context = solver.simplify_symbolically(G)
    assert repr_map[p0] == repr_map[p1]
    assert repr_map[p0] == Range(0 * P.V, 10 * P.V)


@pytest.mark.parametrize(
    "expr_type, operands, expected",
    [
        (Add, (5, 10), 15),
        # (Subtract, (5, 10), -5),
        # (Multiply, (5, 10), 50),
        # (Divide, (5, 10), 0.5),
    ],
)
def test_simple_literal_folds_arithmetic(
    expr_type: type[Arithmetic], operands: Iterable[float], expected: float
):
    expected_result = Quantity_Interval_Disjoint.from_value(expected)
    used_operands = [Quantity_Interval_Disjoint.from_value(o) for o in operands]

    p0 = Parameter(units=dimensionless)
    p1 = Parameter(units=dimensionless)
    p0.alias_is(used_operands[0])
    p1.alias_is(used_operands[1])

    expr = expr_type(p0, p1)
    (expr <= 100.0).constrain()
    G = expr.get_graph()

    solver = DefaultSolver()
    repr_map, context = solver.simplify_symbolically(G)
    logger.info(f"{repr_map.repr_map}")
    deducted_subset = repr_map.try_get_literal(expr, allow_subset=True)
    assert deducted_subset == expected_result


@pytest.mark.parametrize(
    "expr_type, operands, expected",
    [
        (Add, (5, 10), 15),
        (Add, (-5, 15), 10),
        (Add, ((0, 10), 5), (5, 15)),
        (Add, ((0, 10), (-10, 0)), (-10, 10)),
        (Add, (5, 5, 5), 15),
        # (Subtract, (5, 10), -5),
        # (Multiply, (5, 10), 50),
        # (Divide, (5, 10), 0.5),
    ],
)
def test_super_simple_literal_folding(
    expr_type: type[Arithmetic], operands: Iterable[Any], expected: Any
):
    q_operands = [Quantity_Interval_Disjoint.from_value(o) for o in operands]
    expr = expr_type(*q_operands)
    solver = DefaultSolver()

    (expr <= 100.0).constrain()
    G = expr.get_graph()

    repr_map, context = solver.simplify_symbolically(G)
    assert repr_map[expr] == Quantity_Interval_Disjoint.from_value(expected)


def test_literal_folding_add_multiplicative():
    A = Parameter(units=dimensionless)
    B = Parameter(units=dimensionless)

    expr = A + (A * 2) + (5 * A) + B + (A * B * 2) - B
    # expect: 8A + 2AB

    (expr <= 100.0).constrain()

    G = expr.get_graph()
    solver = DefaultSolver()
    repr_map, context = solver.simplify_symbolically(G)

    rep_add = repr_map.repr_map[expr]
    rep_A = repr_map.repr_map[A]
    rep_B = repr_map.repr_map[B]
    assert isinstance(rep_add, Add)
    assert len(rep_add.operands) == 2, f"{rep_add.compact_repr(context)}"
    mul1, mul2 = rep_add.operands

    assert isinstance(mul1, Multiply)
    assert isinstance(mul2, Multiply)
    assert any(
        set(m.operands) == {rep_A, Quantity_Interval_Disjoint.from_value(8)}
        for m in (mul1, mul2)
    )
    assert any(
        set(m.operands) == {rep_A, rep_B, Quantity_Interval_Disjoint.from_value(2)}
        for m in (mul1, mul2)
    )


def test_literal_folding_add_multiplicative_2():
    A = Parameter()
    B = Parameter()

    expr = (
        A
        + (A * 2)
        + Quantity_Interval_Disjoint.from_value(10)
        + (5 * A)
        + Quantity_Interval_Disjoint.from_value(0)
        + B
    )
    (expr <= 100.0).constrain()

    G = expr.get_graph()
    solver = DefaultSolver()
    repr_map, context = solver.simplify_symbolically(G)
    rep_add = repr_map.repr_map[expr]
    a_res = repr_map.repr_map[A]
    b_res = repr_map.repr_map[B]
    assert isinstance(rep_add, Add)
    a_ops = [
        op
        for op in a_res.get_operations()
        if isinstance(op, Multiply)
        and Quantity_Interval_Disjoint.from_value(8) in op.operands
    ]
    assert len(a_ops) == 1
    mul = next(iter(a_ops))
    assert set(rep_add.operands) == {
        b_res,
        Quantity_Interval_Disjoint.from_value(10),
        mul,
    }


def test_transitive_subset():
    A = Parameter(domain=L.Domains.Numbers.REAL())
    B = Parameter(domain=L.Domains.Numbers.REAL())
    C = Parameter(domain=L.Domains.Numbers.REAL())

    A.constrain_subset(B)
    B.constrain_subset(C)

    context = ParameterOperatable.ReprContext()
    for p in (A, B, C):
        p.compact_repr(context)

    C.alias_is(Range(0, 10))

    solver = DefaultSolver()
    result, context = solver.simplify_symbolically(A.get_graph(), context)
    assert result.try_get_literal(A, allow_subset=True) == Range(0, 10)


def test_nested_additions():
    A = Parameter()
    B = Parameter()
    C = Parameter()
    D = Parameter()

    A.alias_is(Quantity_Interval_Disjoint.from_value(1))
    B.alias_is(Quantity_Interval_Disjoint.from_value(1))
    C.alias_is(A + B)
    D.alias_is(C + A)

    solver = DefaultSolver()
    result, _ = solver.simplify_symbolically(A.get_graph())

    assert result.try_get_literal(A) == Quantity_Interval_Disjoint.from_value(1)
    assert result.try_get_literal(B) == Quantity_Interval_Disjoint.from_value(1)
    assert result.try_get_literal(C) == Quantity_Interval_Disjoint.from_value(2)
    assert result.try_get_literal(D) == Quantity_Interval_Disjoint.from_value(3)


def test_combined_add_and_multiply_with_ranges():
    A = Parameter()
    B = Parameter()
    C = Parameter()

    A.alias_is(Range.from_center_rel(1, 0.01))
    B.alias_is(Range.from_center_rel(2, 0.01))
    C.alias_is(2 * A + B)

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(C) == Range.from_center_rel(4, 0.01)


def test_voltage_divider_find_v_out_no_division():
    r_top = Parameter()
    r_bottom = Parameter()
    v_in = Parameter()
    v_out = Parameter()

    v_in.alias_is(Range(9, 10))
    r_top.alias_is(Range(10, 100))
    r_bottom.alias_is(Range(10, 100))
    v_out.alias_is(v_in * r_bottom * ((r_top + r_bottom) ** -1))

    solver = DefaultSolver()

    # dependency problem prevents finding precise solution of [9/11, 100/11]
    # TODO: automatically rearrange expression to match
    # v_out.alias_is(v_in * (1 / (1 + (r_top / r_bottom))))
    assert solver.inspect_get_known_supersets(v_out) == Range(0.45, 50)


def test_voltage_divider_find_v_out_with_division():
    r_top = Parameter()
    r_bottom = Parameter()
    v_in = Parameter()
    v_out = Parameter()

    v_in.alias_is(Range(9, 10))
    r_top.alias_is(Range(10, 100))
    r_bottom.alias_is(Range(10, 100))
    v_out.alias_is(v_in * r_bottom / (r_top + r_bottom))

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(v_out) == Range(0.45, 50)


def test_voltage_divider_find_v_out_single_variable_occurrences():
    r_top = Parameter()
    r_bottom = Parameter()
    v_in = Parameter()
    v_out = Parameter()

    v_in.alias_is(Range(9, 10))
    r_top.alias_is(Range(10, 100))
    r_bottom.alias_is(Range(10, 100))
    v_out.alias_is(v_in * (1 / (1 + (r_top / r_bottom))))

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(v_out) == Range(9 / 11, 100 / 11)


def test_voltage_divider_find_v_in():
    r_top = Parameter()
    r_bottom = Parameter()
    v_in = Parameter()
    v_out = Parameter()

    v_out.alias_is(Range(9, 10))
    r_top.alias_is(Range(10, 100))
    r_bottom.alias_is(Range(10, 100))
    v_out.alias_is(v_in * r_bottom / (r_top + r_bottom))

    solver = DefaultSolver()

    # TODO: should find [9.9, 100]
    assert solver.inspect_get_known_supersets(v_in) == Range(1.8, 200)


def test_voltage_divider_find_resistances():
    r_top = Parameter(units=P.ohm)
    r_bottom = Parameter(units=P.ohm)
    v_in = Parameter(units=P.V)
    v_out = Parameter(units=P.V)
    r_total = Parameter(units=P.ohm)

    v_in.alias_is(Range(9 * P.V, 10 * P.V))
    v_out.alias_is(Range(0.9 * P.V, 1 * P.V))
    r_total.alias_is(Quantity_Interval_Disjoint.from_value(100 * P.ohm))
    r_total.alias_is(r_top + r_bottom)
    v_out.alias_is(v_in * r_bottom / (r_top + r_bottom))

    solver = DefaultSolver()
    # FIXME: this test looks funky
    assert solver.inspect_get_known_supersets(v_out) == Range(0.9 * P.V, 1 * P.V)

    # TODO: specify r_top (with tolerance), finish solving to find r_bottom


def test_voltage_divider_find_r_top():
    r_top = Parameter(units=P.ohm)
    r_bottom = Parameter(units=P.ohm)
    v_in = Parameter(units=P.V)
    v_out = Parameter(units=P.V)

    v_in.alias_is(Range.from_center_rel(10 * P.V, 0.01))
    v_out.alias_is(Range.from_center_rel(1 * P.V, 0.01))
    r_bottom.alias_is(Range.from_center_rel(1 * P.ohm, 0.01))
    v_out.alias_is(v_in * r_bottom / (r_top + r_bottom))
    # r_top = (v_in * r_bottom) / v_out - r_bottom

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(r_top) == Range(
        (10 * 0.99**2) / 1.01 - 1.01, (10 * 1.01**2) / 0.99 - 0.99
    )


def test_voltage_divider_reject_invalid_r_top():
    r_top = Parameter(units=P.ohm)
    r_bottom = Parameter(units=P.ohm)
    v_in = Parameter(units=P.V)
    v_out = Parameter(units=P.V)

    v_in.alias_is(Range.from_center_rel(10 * P.V, 0.01))
    v_out.alias_is(Range.from_center_rel(1 * P.V, 0.01))
    v_out.alias_is(v_in * r_bottom / (r_top + r_bottom))

    r_bottom.alias_is(Range.from_center_rel(1 * P.ohm, 0.01))
    r_top.alias_is(Range.from_center_rel(999 * P.ohm, 0.01))

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(r_top.get_graph())


def test_base_unit_switch():
    A = Parameter(units=P.mAh)
    A.alias_is(Range(100 * P.mAh, 600 * P.mAh))
    (A >= 100 * P.mAh).constrain()

    G = A.get_graph()
    solver = DefaultSolver()
    repr_map, context = solver.simplify_symbolically(G)
    assert repr_map[A] == RangeWithGaps.from_value((100 * P.mAh, 600 * P.mAh))


@pytest.mark.parametrize("predicate_type", [Is, IsSubset])
def test_assert_any_predicate_super_basic(predicate_type: type[Predicate]):
    p0 = Parameter(units=P.V)
    p0.alias_is(Range(0 * P.V, 10 * P.V))

    solver = DefaultSolver()
    pred = predicate_type(p0, Range(0 * P.V, 10 * P.V))
    result = solver.assert_any_predicate([(pred, None)], lock=False)
    assert result.true_predicates == [(pred, None)]
    assert result.false_predicates == []
    assert result.unknown_predicates == []


def test_congruence_filter():
    A = Parameter(domain=L.Domains.ENUM(F.LED.Color))
    x = Is(A, EnumSet(F.LED.Color.EMERALD))

    y1 = Not(x).constrain()
    y2 = Not(x).constrain()
    assert y1.is_congruent_to(y2)

    solver = DefaultSolver()
    result, context = solver.simplify_symbolically(x.get_graph())
    assert result.repr_map[y1] is result.repr_map[y2]


def test_inspect_enum_simple():
    A = Parameter(domain=L.Domains.ENUM(F.LED.Color))

    A.constrain_subset(F.LED.Color.EMERALD)

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(A) == F.LED.Color.EMERALD


def test_inspect_enum_led():
    led = F.LED()

    led.color.constrain_subset(F.LED.Color.EMERALD)

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(led.color) == F.LED.Color.EMERALD


@pytest.mark.usefixtures("setup_project_config")
def test_simple_pick():
    led = F.LED()

    solver = DefaultSolver()
    pick_module_by_params(
        led,
        solver,
        [
            PickerOption(
                part=LCSC_Part(partno="C72043"),
                params={
                    "color": L.EnumSet(F.LED.Color.EMERALD),
                    "max_brightness": 285 * P.mcandela,
                    "forward_voltage": L.Single(3.7 * P.volt),
                    "max_current": 100 * P.mA,
                },
                pinmap={"1": led.cathode, "2": led.anode},
            ),
        ],
    )

    assert led.has_trait(F.has_part_picked)
    assert led.get_trait(F.has_part_picked).get_part().partno == "C72043"


def test_simple_negative_pick():
    led = F.LED()
    led.color.constrain_subset(L.EnumSet(F.LED.Color.RED, F.LED.Color.BLUE))

    solver = DefaultSolver()
    pick_module_by_params(
        led,
        solver,
        [
            PickerOption(
                part=LCSC_Part(partno="C72043"),
                params={
                    "color": L.EnumSet(F.LED.Color.EMERALD),
                    "max_brightness": 285 * P.mcandela,
                    "forward_voltage": L.Single(3.7 * P.volt),
                    "max_current": 100 * P.mA,
                },
                pinmap={"1": led.cathode, "2": led.anode},
            ),
            PickerOption(
                part=LCSC_Part(partno="C72041"),
                params={
                    "color": L.EnumSet(F.LED.Color.BLUE),
                    "max_brightness": 28.5 * P.mcandela,
                    "forward_voltage": L.Single(3.1 * P.volt),
                    "max_current": 100 * P.mA,
                },
                pinmap={"1": led.cathode, "2": led.anode},
            ),
        ],
    )

    assert led.has_trait(F.has_part_picked)
    assert led.get_trait(F.has_part_picked).get_part().partno == "C72041"


def test_jlcpcb_pick_resistor():
    resistor = F.Resistor()
    resistor.resistance.constrain_subset(L.Range(10 * P.ohm, 100 * P.ohm))

    solver = DefaultSolver()
    pick_part_recursively(resistor, solver)

    assert resistor.has_trait(F.has_part_picked)
    print(resistor.get_trait(F.has_part_picked).get_part())


def test_jlcpcb_pick_capacitor():
    capacitor = F.Capacitor()
    capacitor.capacitance.constrain_subset(L.Range(100 * P.nF, 1 * P.uF))
    capacitor.max_voltage.constrain_ge(50 * P.V)

    solver = DefaultSolver()
    pick_part_recursively(capacitor, solver)

    assert capacitor.has_trait(F.has_part_picked)
    print(capacitor.get_trait(F.has_part_picked).get_part())


def test_jlcpcb_pick_led():
    led = F.LED()
    led.color.constrain_subset(L.EnumSet(F.LED.Color.EMERALD))
    led.max_current.constrain_ge(10 * P.mA)

    solver = DefaultSolver()
    pick_part_recursively(led, solver)

    assert led.has_trait(F.has_part_picked)
    print(led.get_trait(F.has_part_picked).get_part())


def test_jlcpcb_pick_powered_led():
    led = F.PoweredLED()
    led.led.color.constrain_subset(L.EnumSet(F.LED.Color.EMERALD))
    led.power.voltage.constrain_subset(L.Range(1.8 * P.volt, 5.5 * P.volt))

    solver = DefaultSolver()
    children_mods = led.get_children_modules(direct_only=False, types=(Module,))

    pick_part_recursively(led, solver)

    picked_parts = [mod for mod in children_mods if mod.has_trait(F.has_part_picked)]
    assert len(picked_parts) == 2
    print([(p, p.get_trait(F.has_part_picked).get_part()) for p in picked_parts])


@pytest.mark.parametrize(
    "op, x_op_y, y, x_expected",
    [
        (
            Add,
            Range.from_center_rel(3, 0.01),
            Range.from_center_rel(1, 0.01),
            Range.from_center_rel(2, 0.02),
        )
    ],
)
def test_simple_parameter_isolation(
    op: type[Arithmetic], x_op_y: Range, y: Range, x_expected: Range
):
    X = Parameter()
    Y = Parameter()

    op(X, Y).alias_is(x_op_y)
    Y.alias_is(y)

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(X) == x_expected


def test_abstract_lowpass():
    Li = Parameter(units=P.H)
    C = Parameter(units=P.F)
    fc = Parameter(units=P.Hz)

    # formula
    fc.alias_is(1 / (2 * math.pi * (C * Li).operation_sqrt()))

    # input
    Li.alias_is(Range.from_center_rel(1 * P.uH, 0.01))
    fc.alias_is(Range.from_center_rel(1000 * P.Hz, 0.01))

    # solve
    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(C) == Range(
        6.158765796 * P.GF, 6.410118344 * P.GF
    )


def test_param_isolation():
    X = Parameter()
    Y = Parameter()

    (X + Y).alias_is(Range.from_center_rel(3, 0.01))
    Y.alias_is(Range.from_center_rel(1, 0.01))

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(X) == Range.from_center_rel(2, 0.02)


@pytest.mark.parametrize(
    "op",
    [
        add,
        mul,
        sub,
        truediv,
    ],
)
def test_extracted_literal_folding(op):
    A = Parameter()
    B = Parameter()
    C = Parameter(domain=L.Domains.Numbers.REAL())

    lit1 = Range(0, 10)
    lit2 = Range(10, 20)
    lito = op(lit1, lit2)

    A.alias_is(lit1)
    B.alias_is(lit2)

    op(A, B).alias_is(C)

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(C) == lito


def test_fold_pow():
    A = Parameter()
    B = Parameter()

    lit = RangeWithGaps(Range(5, 6))
    lit_operand = 2

    A.alias_is(lit)
    B.alias_is(A**lit_operand)

    solver = DefaultSolver()
    repr_map, _ = solver.simplify_symbolically(B.get_graph())

    res = repr_map.try_get_literal(B)
    assert res == lit**lit_operand


def test_graph_split():
    class App(Module):
        A: Parameter
        B: Parameter

    app = App()

    C = Parameter()
    D = Parameter()
    app.A.alias_is(C)
    app.B.alias_is(D)

    context = ParameterOperatable.ReprContext()
    for p in (app.A, app.B, C, D):
        p.compact_repr(context)

    solver = DefaultSolver()
    repr_map, _ = solver.simplify_symbolically(app.get_graph(), context)

    assert (
        repr_map.repr_map[app.A].get_graph() is not repr_map.repr_map[app.B].get_graph()
    )


def test_ss_single_into_alias():
    A = Parameter()
    B = Parameter()

    A.alias_is(Range(5, 10))
    B.operation_is_subset(5).constrain()
    C = A + B

    solver = DefaultSolver()
    repr_map, _ = solver.simplify_symbolically(C.get_graph())

    assert repr_map.try_get_literal(B) == 5
    assert repr_map.try_get_literal(A) == Range(5, 10)


@pytest.mark.parametrize(
    "op, invert",
    [
        (GreaterOrEqual, False),
        (LessOrEqual, True),
        (Is, True),
        (Is, False),
        (IsSubset, True),
        (IsSubset, False),
        (IsSuperset, True),
        (IsSuperset, False),
    ],
)
def test_find_contradiction_by_predicate(op, invert):
    """
    A > B, A is [0, 10], B is [20, 30], A further uncorrelated B
    -> [0,10] > [20, 30]
    """

    A = Parameter()
    B = Parameter()

    A.alias_is(Range(0, 10))
    B.alias_is(Range(20, 30))

    if invert:
        op(B, A).constrain()
    else:
        op(A, B).constrain()

    solver = DefaultSolver()

    with pytest.raises(Contradiction):
        solver.simplify_symbolically(A.get_graph())


def test_find_contradiction_by_gt():
    A = Parameter()
    B = Parameter()

    A.alias_is(Range(0, 10))
    B.alias_is(Range(20, 30))

    (A > B).constrain()

    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.simplify_symbolically(A.get_graph())


def test_can_add_parameters():
    A = Parameter()
    B = Parameter()
    C = Parameter()

    A.alias_is(Range(10, 100))
    B.alias_is(Range(10, 100))
    C.alias_is((A + B))

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(C) == Range(20, 200)


def test_ss_estimation_ge():
    A = Parameter()
    B = Parameter()

    A.operation_is_subset(Range(0, 10)).constrain()
    (B >= A).constrain()

    solver = DefaultSolver()
    solver.simplify_symbolically(B.get_graph())


def test_fold_mul_zero():
    A = Parameter()
    B = Parameter()
    C = Parameter()

    A.alias_is(0)
    B.alias_is(Range(10, 20))

    (A * B).alias_is(C)

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(C) == 0


def test_fold_or_true():
    A = Parameter(domain=L.Domains.BOOL())
    B = Parameter(domain=L.Domains.BOOL())
    C = Parameter(domain=L.Domains.BOOL())

    A.alias_is(True)

    (A | B).alias_is(C)

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(C) == BoolSet(True)


def test_fold_not():
    A = Parameter(domain=L.Domains.BOOL())
    B = Parameter(domain=L.Domains.BOOL())

    A.alias_is(False)
    (Not(A)).alias_is(B)

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(B) == BoolSet(True)


def test_fold_ss_transitive():
    A = Parameter()
    B = Parameter()
    C = Parameter()

    C.operation_is_subset(Range(0, 10)).constrain()
    B.operation_is_subset(C).constrain()
    A.operation_is_subset(B).constrain()

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(A) == Range(0, 10)


def test_ss_intersect():
    A = Parameter()
    B = Parameter()
    C = Parameter()

    A.alias_is(Range(0, 15))
    B.alias_is(Range(10, 20))
    C.constrain_subset(A)
    C.constrain_subset(B)

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(C) == Range(10, 15)


@pytest.mark.parametrize(
    "left, right, expected",
    [
        (
            [Range(0, 10)],
            [Range(0, 10)],
            (True, False),
        ),
        (
            [Range(0, 10)],
            [Range(10, 20)],
            (False, False),
        ),
        (
            [Add(Range(0, 10), Range(0, 20))],
            [Add(Range(0, 10), Range(0, 20))],
            (True, False),
        ),
        (
            [Add(Range(0, 10), Range(0, 20))],
            [Add(Range(0, 20), Range(0, 10))],
            (True, False),
        ),
        (
            [Not(BoolSet(True))],
            [Not(BoolSet(True))],
            (True, True),
        ),
        (
            [Not(Not(BoolSet(True)))],
            [Not(Not(BoolSet(True)))],
            (True, True),
        ),
        (
            [Multiply(Range(0, 10), Range(0, 10))],
            [Multiply(Range(0, 10), Range(0, 10))],
            (True, False),
        ),
        (
            [Multiply(Range(0, math.inf), Range(0, math.inf), Range(0, math.inf))],
            [Multiply(Range(0, math.inf), Range(0, math.inf))],
            (False, False),
        ),
        (
            [Add(Range(0, math.inf), Range(0, math.inf))],
            [Add(Range(0, math.inf))],
            (False, False),
        ),
    ],
)
def test_congruence_lits(left, right, expected):
    assert (
        Expression.are_pos_congruent(left, right, allow_uncorrelated=True)
        == expected[0]
    )
    assert Expression.are_pos_congruent(left, right) == expected[1]


def test_fold_literals():
    A = Parameter()
    A.alias_is(Add(Range(0, 10), Range(0, 10)))

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(A) == Range(0, 20)


def test_deduce_negative():
    A = Parameter(domain=L.Domains.BOOL())

    p = Not(A)

    solver = DefaultSolver()
    res = solver.assert_any_predicate([(p, None)], lock=False)
    assert res.true_predicates == [(p, None)]


def test_empty_and():
    solver = DefaultSolver()

    p = And()
    res = solver.assert_any_predicate([(p, None)], lock=False)
    assert res.true_predicates == [(p, None)]


def test_implication():
    A = Parameter()
    B = Parameter()

    A.constrain_subset(DiscreteSet(5, 10))

    A.operation_is_subset(Single(5)).operation_implies(
        B.operation_is_subset(Range.from_center_rel(100, 0.1))
    ).constrain()
    A.operation_is_subset(Single(10)).operation_implies(
        B.operation_is_subset(Range.from_center_rel(500, 0.1))
    ).constrain()

    A.constrain_subset(Single(10))

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(B) == Range.from_center_rel(500, 0.1)


@pytest.mark.parametrize("A_value", [5, 10, 15])
def test_mapping(A_value):
    A = Parameter()
    B = Parameter()

    X = Range.from_center_rel(100, 0.1)
    Y = Range.from_center_rel(200, 0.1)
    Z = Range.from_center_rel(300, 0.1)

    mapping = {5: X, 10: Y, 15: Z}
    A.constrain_mapping(B, mapping)  # type: ignore

    A.constrain_subset(A_value)

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(B) == mapping[A_value]


@pytest.mark.parametrize("op", [Subtract, sub, Add, add])
def test_subtract_zero(op):
    from faebryk.core.solver.utils import make_lit

    A = Parameter()
    A.alias_is(op(make_lit(1), make_lit(0)))

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(A) == make_lit(1)


def test_canonical_subtract_zero():
    from faebryk.core.solver.utils import make_lit

    A = Parameter()
    A.alias_is(Multiply(make_lit(0), make_lit(-1)))

    B = Parameter()
    B.alias_is(Add(make_lit(1), Multiply(make_lit(0), make_lit(-1))))

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(A) == make_lit(0)
    assert solver.inspect_get_known_supersets(B) == make_lit(1)


def test_nested_fold_scalar():
    from faebryk.core.solver.utils import make_lit

    A = Parameter()
    A.alias_is(Add(make_lit(1), Multiply(make_lit(2), make_lit(3))))

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(A) == make_lit(7)


def test_regression_lit_mul_fold_powers():
    A = Parameter()
    A.alias_is(Power(2, -1) * Power(2, 0.5))

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(A) == 2**-0.5


def test_nested_fold_interval():
    A = Parameter()
    A.alias_is(
        Add(
            Range.from_center_rel(1, 0.1),
            Multiply(Range.from_center_rel(2, 0.1), Range.from_center_rel(3, 0.1)),
        )
    )

    solver = DefaultSolver()
    assert solver.inspect_get_known_supersets(A) == Range(5.76, 8.36)


# XFAIL --------------------------------------------------------------------------------


# extra formula
# C.alias_is(1 / (4 * math.pi**2 * Li * fc**2))
# TODO test with only fc given
@pytest.mark.xfail(reason="Need more powerful expression reordering")  # TODO
def test_abstract_lowpass_ss():
    Li = Parameter(units=P.H)
    C = Parameter(units=P.F)
    fc = Parameter(units=P.Hz)

    # formula
    fc.alias_is(1 / (2 * math.pi * (C * Li).operation_sqrt()))

    # input
    Li_const = RangeWithGaps(Range.from_center_rel(1 * P.uH, 0.01))
    fc_const = RangeWithGaps(Range.from_center_rel(1000 * P.Hz, 0.01))
    Li.constrain_subset(Li_const)
    fc.constrain_subset(fc_const)

    # solve
    solver = DefaultSolver()
    solver.simplify_symbolically(fc.get_graph())

    C_expected = 1 / (4 * math.pi**2 * Li_const * fc_const**2)

    assert solver.inspect_get_known_supersets(C) == C_expected


@pytest.mark.xfail(reason="Need more powerful expression reordering")  # TODO
def test_voltage_divider_find_r_bottom():
    r_top = Parameter(units=P.ohm)
    r_bottom = Parameter(units=P.ohm)
    v_in = Parameter(units=P.V)
    v_out = Parameter(units=P.V)

    # formula
    v_out.alias_is(v_in * r_bottom / (r_top + r_bottom))

    # input
    v_in.alias_is(Range.from_center_rel(10 * P.V, 0.01))
    v_out.alias_is(Range.from_center_rel(1 * P.V, 0.01))
    r_top.alias_is(Range.from_center_rel(9 * P.ohm, 0.01))

    solver = DefaultSolver()

    assert solver.inspect_get_known_supersets(r_bottom) == Range.from_center_rel(
        1 * P.ohm, 0.01
    )


@pytest.mark.xfail(reason="TODO reenable ge fold")
def test_min_max_single():
    p0 = Parameter(units=P.V)
    p0.alias_is(L.Range(0 * P.V, 10 * P.V))

    p1 = Parameter(units=P.V)
    p1.alias_is(Max(p0))

    solver = DefaultSolver()
    out = solver.inspect_get_known_supersets(p1)
    assert out == L.Single(10 * P.V)


@pytest.mark.xfail(reason="TODO")
def test_min_max_multi():
    p0 = Parameter(units=P.V)
    p0.alias_is(L.Range(0 * P.V, 10 * P.V))
    p3 = Parameter(units=P.V)
    p3.alias_is(L.Range(4 * P.V, 15 * P.V))

    p1 = Parameter(units=P.V)
    p1.alias_is(Max(p0, p3))

    solver = DefaultSolver()
    out = solver.inspect_get_known_supersets(p1)
    assert out == L.Single(15 * P.V)


@pytest.mark.xfail(
    reason="Behaviour not implemented https://github.com/atopile/atopile/issues/615"
)
def test_symmetric_inequality_uncorrelated():
    p0 = Parameter(units=P.V)
    p1 = Parameter(units=P.V)

    p0.alias_is(Range(0 * P.V, 10 * P.V))

    (p0 >= p1).constrain()
    (p0 <= p1).constrain()

    # This would only work if p0 is alias p1
    # but we never do implicit alias, because that's very dangerous
    # so this has to throw

    # strategy: if this kind of unequality exists, check if there is an alias
    # and if not, throw

    G = p0.get_graph()
    solver = DefaultSolver()

    with pytest.raises(Contradiction):
        solver.simplify_symbolically(G)


def test_fold_correlated():
    """
    ```
    A is [5, 10], B is [10, 15]
    B is A + 5
    B - A | [10, 15] - [5, 10] = [0, 10] BUT SHOULD BE 5
    ```

    A and B correlated, thus B - A should do ss not alias
    """

    A = Parameter()
    B = Parameter()
    C = Parameter()

    op = add
    op_inv = sub

    lit1 = Range(5, 10)
    lit_operand = Single(5)
    lit2 = op(lit1, lit_operand)

    A.alias_is(lit1)
    B.alias_is(lit2)
    B.alias_is(op(A, lit_operand))

    C.alias_is(op_inv(B, A))

    context = ParameterOperatable.ReprContext()
    for p in (A, B, C):
        p.compact_repr(context)

    solver = DefaultSolver()
    repr_map, _ = solver.simplify_symbolically(C.get_graph(), context)

    is_lit = repr_map.try_get_literal(C, allow_subset=False)
    ss_lit = repr_map.try_get_literal(C, allow_subset=True)
    assert ss_lit is not None

    # Test for ss estimation
    assert ss_lit.is_subset_of(op_inv(lit2, lit1))
    # Test for not wrongful is estimation
    assert is_lit != op_inv(lit2, lit1)

    # Test for correct is estimation
    try:
        assert is_lit == lit_operand
    except AssertionError:
        pytest.xfail("TODO")


@pytest.mark.parametrize(
    "op,lits,expected",
    [
        (Add, [], 0),
        (Add, [1, 2, 3, 4, 5], 15),
        (Multiply, [1, 2, 3, 4, 5], 120),
        (Multiply, [], 1),
        (Power, [2, 3], 8),
        (Round, [2.4], 2),
        (Round, [Range(-2.6, 5.3)], Range(-3, 5)),
        (Abs, [-2], 2),
        (Abs, [Range(-2, 3)], Range(0, 3)),
        (Sin, [0], 0),
        (Sin, [Range(0, 2 * math.pi)], Range(-1, 1)),
        (Log, [10], math.log(10)),
        (Log, [Range(1, 10)], Range(math.log(1), math.log(10))),
        (Or, [False, False, True], True),
        (Or, [False, BoolSet(True, False), True], True),
        (Or, [], False),
        (Not, [False], True),
        (Intersection, [Range(0, 10), Range(10, 20)], Range(10, 10)),
        (Union, [Range(0, 10), Range(10, 20)], Range(0, 20)),
        (SymmetricDifference, [Range(0, 10), Range(10, 20)], Range(0, 20)),
        (
            SymmetricDifference,
            [Range(0, 10), Range(5, 20)],
            RangeWithGaps(Range(0, 5), Range(10, 20)),
        ),
        (Is, [Range(0, 10), Range(0, 10)], True),
        (GreaterOrEqual, [Range(10, 20), Range(0, 10)], True),
        (GreaterOrEqual, [Range(5, 20), Range(0, 10)], BoolSet(True, False)),
        (GreaterThan, [Range(10, 20), Range(0, 10)], BoolSet(True, False)),
        (GreaterThan, [Range(0, 10), Range(10, 20)], False),
        (IsSubset, [Range(0, 10), Range(0, 20)], True),
    ],
)
def test_exec_pure_literal_expressions(op: type[CanonicalExpression], lits, expected):
    from faebryk.core.solver.literal_folding import _exec_pure_literal_expressions
    from faebryk.core.solver.utils import make_lit

    lits_converted = list(map(make_lit, lits))
    expected_converted = make_lit(expected)

    expr = op(*lits_converted)
    assert _exec_pure_literal_expressions(expr) == expected_converted

    if op is GreaterThan:
        pytest.xfail("GreaterThan is not supported in solver")

    def _get_param_from_lit(lit: CanonicalLiteral):
        if isinstance(lit, BoolSet):
            p = Parameter(domain=L.Domains.BOOL())
        elif isinstance(lit, Quantity_Set):
            p = Parameter(domain=L.Domains.Numbers.REAL())
        else:
            raise NotImplementedError()
        return p

    result = _get_param_from_lit(expected_converted)
    result.alias_is(expr)

    solver = DefaultSolver()
    repr_map, _ = solver.simplify_symbolically(result.get_graph())
    assert repr_map.try_get_literal(result) == expected_converted
