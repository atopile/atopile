# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Any, Iterable

import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import (
    Add,
    And,
    Arithmetic,
    Is,
    IsSubset,
    Multiply,
    Or,
    Parameter,
    ParameterOperatable,
    Predicate,
    Subtract,
)
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.utils import Contradiction, ContradictionByLiteral
from faebryk.libs.library import L
from faebryk.libs.library.L import Range, RangeWithGaps
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval_Disjoint,
)
from faebryk.libs.sets.sets import BoolSet
from faebryk.libs.units import P, dimensionless, quantity

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
    voltage3.alias_is(Range(4 * P.V, 6 * P.V))

    solver.phase_one_no_guess_solving(voltage1.get_graph())


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
    (acc < quantity(11, dimensionless)).constrain()

    G = acc.get_graph()
    solver = DefaultSolver()
    solver.phase_one_no_guess_solving(G)


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
    solver.phase_one_no_guess_solving(G)
    # TODO actually test something


def test_shortcircuit_logic_and():
    p0 = Parameter(domain=L.Domains.BOOL())
    expr = p0 & False
    expr.constrain()
    G = expr.get_graph()
    solver = DefaultSolver()

    with pytest.raises(ContradictionByLiteral):
        solver.phase_one_no_guess_solving(G)


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
    repr_map = solver.phase_one_no_guess_solving(G)
    assert repr_map[ored] == BoolSet(True)


def test_inequality_to_set():
    p0 = Parameter(units=dimensionless)
    p0.constrain_le(2.0)
    p0.constrain_ge(1.0)
    G = p0.get_graph()
    solver = DefaultSolver()
    solver.phase_one_no_guess_solving(G)


def test_remove_obvious_tautologies():
    p0, p1, p2 = (Parameter(units=dimensionless) for _ in range(3))
    p0.alias_is(p1 + p2)
    p1.constrain_ge(0.0)
    p2.constrain_ge(0.0)
    p2.alias_is(p2)

    G = p0.get_graph()
    solver = DefaultSolver()
    solver.phase_one_no_guess_solving(G)


def test_subset_of_literal():
    p0, p1, p2 = (
        Parameter(units=dimensionless, within=Range(0, i, units=dimensionless))
        for i in range(3)
    )
    p0.alias_is(p1)
    p1.alias_is(p2)

    G = p0.get_graph()
    solver = DefaultSolver()
    solver.phase_one_no_guess_solving(G)


def test_alias_classes():
    p0, p1, p2, p3, p4 = (
        Parameter(units=dimensionless, within=Range(0, i)) for i in range(5)
    )
    p0.alias_is(p1)
    addition = p2 + p3
    p1.alias_is(addition)
    addition2 = p3 + p2
    p4.alias_is(addition2)

    G = p0.get_graph()
    solver = DefaultSolver()
    solver.phase_one_no_guess_solving(G)


def test_solve_realworld():
    app = F.RP2040()
    solver = DefaultSolver()
    solver.phase_one_no_guess_solving(app.get_graph())


def test_inspect_known_superranges():
    p0 = Parameter(units=P.V, within=Range(1 * P.V, 10 * P.V))
    p0.alias_is(Range(1 * P.V, 3 * P.V) + Range(4 * P.V, 6 * P.V))
    solver = DefaultSolver()
    assert solver.inspect_get_known_superranges(p0) == RangeWithGaps((5 * P.V, 9 * P.V))


def test_symmetric_inequality_uncorrelated():
    p0 = Parameter(units=P.V)
    p1 = Parameter(units=P.V)

    p0.alias_is(Range(0 * P.V, 10 * P.V))

    (p0 >= p1).constrain()
    (p0 <= p1).constrain()

    G = p0.get_graph()
    solver = DefaultSolver()

    with pytest.raises(Contradiction):
        solver.phase_one_no_guess_solving(G)


def test_obvious_contradiction_by_literal():
    p0 = Parameter(units=P.V)
    p1 = Parameter(units=P.V)

    p0.alias_is(Range(0 * P.V, 10 * P.V))
    p1.alias_is(Range(5 * P.V, 10 * P.V))

    p0.alias_is(p1)

    G = p0.get_graph()
    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        solver.phase_one_no_guess_solving(G)


def test_less_obvious_contradiction_by_literal():
    A = Parameter(units=P.V)
    B = Parameter(units=P.V)
    C = Parameter(units=P.V)

    A.alias_is(Range(0.0 * P.V, 10.0 * P.V))
    B.alias_is(Range(5.0 * P.V, 10.0 * P.V))
    C.alias_is(A + B)
    C.alias_is(Range(0.0 * P.V, 15.0 * P.V))

    G = A.get_graph()
    solver = DefaultSolver()
    with pytest.raises(ContradictionByLiteral):
        repr_map = solver.phase_one_no_guess_solving(G)
        from faebryk.core.graph import GraphFunctions

        for op in GraphFunctions(repr_map.repr_map[A].get_graph()).nodes_of_type(
            ParameterOperatable
        ):
            logger.info(f"{op!r}")
    # FIME
    # <*3548|Parameter> is 5-10               subset 0-inf
    # <*3158|Parameter> is 5-20 is Add(P)
    # <*35D8|Parameter> is Add(P, P) is 0-15  subset 0-inf | Add(P,P) subset 3158 is 5-20 SHOULD DETECT CONTRADICTION HERE
    # <*3668|Parameter> is 0-10               subset 0-inf

    # <*3428|Add>((Quantity_Interval_Disjoint([5.0, 20.0]),))
    # <*3278|Add>((Quantity_Interval_Disjoint([5.0, 20.0]),))
    # <*3788|Add>((<*3668|Parameter>, <*3548|Parameter>))
    # <*3308|Add>((Quantity_Interval_Disjoint([5.0, 20.0]),))

    # <*3938|Is>((<*3668|Parameter>, Quantity_Interval_Disjoint([0.0, 10.0])))
    # <*C338|Is>((<*35D8|Parameter>, <*3788|Add>((<*3668|Parameter>, <*3548|Parameter>))))
    # <*3A58|Is>((<*35D8|Parameter>, Quantity_Interval_Disjoint([0.0, 15.0])))
    # <*3AE8|Is>((<*3158|Parameter>, Quantity_Interval_Disjoint([5.0, 20.0])))
    # <*3C08|Is>((<*3158|Parameter>, Quantity_Interval_Disjoint([5.0, 20.0])))
    # <*38A8|Is>((<*3548|Parameter>, Quantity_Interval_Disjoint([5.0, 10.0])))
    # <*34B8|Is>((<*3428|Add>((Quantity_Interval_Disjoint([5.0, 20.0]),)), <*3158|Parameter>))
    # <*31E8|Is>((<*3278|Add>((Quantity_Interval_Disjoint([5.0, 20.0]),)), <*3158|Parameter>))
    # <*3398|Is>((<*3308|Add>((Quantity_Interval_Disjoint([5.0, 20.0]),)), <*3158|Parameter>))

    # <*39C8|IsSubset>((<*3668|Parameter>, Quantity_Interval_Disjoint([0.0, inf])))
    # <*3B78|IsSubset>((<*3548|Parameter>, Quantity_Interval_Disjoint([0.0, inf])))
    # <*36F8|IsSubset>((<*35D8|Parameter>, Quantity_Interval_Disjoint([0.0, inf])))
    # <*3818|IsSubset>((<*3158|Parameter>, <*3158|Parameter>))
    # <*3C98|IsSubset>((<*3788|Add>((<*3668|Parameter>, <*3548|Parameter>)), <*3158|Parameter>))
    # <*C218|IsSubset>((<*3788|Add>((<*3668|Parameter>, <*3548|Parameter>)), <*3158|Parameter>))
    # <*3E48|IsSubset>((<*3788|Add>((<*3668|Parameter>, <*3548|Parameter>)), Quantity_Interval_Disjoint([5.0, 20.0])))


def test_symmetric_inequality_correlated():
    p0 = Parameter(units=P.V)
    p1 = Parameter(units=P.V)

    p0.alias_is(Range(0 * P.V, 10 * P.V))
    p1.alias_is(p0)

    (p0 >= p1).constrain()
    (p0 <= p1).constrain()

    G = p0.get_graph()
    solver = DefaultSolver()
    repr_map = solver.phase_one_no_guess_solving(G)
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
    repr_map = solver.phase_one_no_guess_solving(G)
    logger.info(f"{repr_map.repr_map}")
    deducted_subset = repr_map.try_get_literal(expr, IsSubset)
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

    (expr < 100.0).constrain()
    G = expr.get_graph()

    repr_map = solver.phase_one_no_guess_solving(G)
    assert repr_map[expr] == Quantity_Interval_Disjoint.from_value(expected)


def test_literal_folding_add_multiplicative():
    A = Parameter(units=dimensionless)

    expr = A + (A * 2) + (5 * A)
    (expr <= 100.0).constrain()

    G = expr.get_graph()
    solver = DefaultSolver()
    repr_map = solver.phase_one_no_guess_solving(G)
    rep_add = repr_map.repr_map[expr]
    a_res = repr_map.repr_map[A]
    assert isinstance(rep_add, Multiply)
    assert set(rep_add.operands) == {
        a_res,
        Quantity_Interval_Disjoint.from_value(8),
    }


def test_literal_folding_add_multiplicative_2():
    A = Parameter(units=dimensionless)
    B = Parameter(units=dimensionless)

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
    repr_map = solver.phase_one_no_guess_solving(G)
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


@pytest.mark.parametrize(
    "predicate_type",
    [
        Is,
        IsSubset,
    ],
)
def test_assert_any_predicate_super_basic(predicate_type: type[Predicate]):
    p0 = Parameter(units=P.V)
    p0.alias_is(Range(0 * P.V, 10 * P.V))

    solver = DefaultSolver()
    pred = predicate_type(p0, Range(0 * P.V, 10 * P.V))
    result = solver.assert_any_predicate([(pred, None)], lock=False)
    assert result.true_predicates == [(pred, None)]
    assert result.false_predicates == []
    assert result.unknown_predicates == []


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()
    typer.run(test_shortcircuit_logic_and)
