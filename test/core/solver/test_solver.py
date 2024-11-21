# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Iterable

import pytest

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import (
    Add,
    And,
    Arithmetic,
    Parameter,
    ParameterOperatable,
    Subtract,
)
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.core.solver.utils import Contradiction
from faebryk.libs.library import L
from faebryk.libs.library.L import Range, RangeWithGaps
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


def test_simplify_logic():
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


def test_inequality_to_set():
    p0 = Parameter(units=dimensionless)
    p0.constrain_le(2 * dimensionless)
    p0.constrain_ge(1 * dimensionless)
    G = p0.get_graph()
    solver = DefaultSolver()
    solver.phase_one_no_guess_solving(G)


def test_remove_obvious_tautologies():
    p0, p1, p2 = (Parameter(units=dimensionless) for _ in range(3))
    p0.alias_is(p1 + p2)
    p1.constrain_ge(0)
    p2.constrain_ge(0)
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
    expected_result = quantity(float(expected), dimensionless)
    used_operands = [quantity(float(o), dimensionless) for o in operands]

    p0 = Parameter(units=dimensionless)
    p1 = Parameter(units=dimensionless)
    p0.alias_is(used_operands[0])
    p1.alias_is(used_operands[1])

    expr = expr_type(p0, p1)
    G = expr.get_graph()

    solver = DefaultSolver()
    repr_map = solver.phase_one_no_guess_solving(G)
    assert repr_map[expr] == expected_result


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()
    typer.run(test_symmetric_inequality_correlated)
