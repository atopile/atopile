# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

from faebryk.core.parameter import (
    Add,
    And,
    Difference,
    Divide,
    Expression,
    Intersection,
    Is,
    Logic,
    Multiply,
    Or,
    Parameter,
    ParameterOperatable,
    Subtract,
    Union,
    Xor,
)
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import (
    Associative,
    FullyAssociative,
    algorithm,
    flatten_associative,
    get_expressions_involved_in,
)
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import cast_assert, times

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "op",
    [
        Add,
        Multiply,
        Subtract,
        Divide,
        And,
        Or,
        Xor,
        Union,
        Intersection,
        Difference,
    ],
)
def test_flatten_associative(op: type[Expression]):
    def flatten(op):
        return flatten_associative(op, lambda _, __: True)

    if issubclass(op, Logic):
        domain = L.Domains.BOOL()
    else:
        domain = L.Domains.Numbers.REAL()

    A, B, C, D, E = times(5, lambda: Parameter(domain=domain))

    to_flatten = op(op(A, B), C, op(D, E))
    res = flatten(to_flatten)

    if not issubclass(op, Associative):
        assert len(res.destroyed_operations) == 0
        assert set(res.extracted_operands) == set(to_flatten.operands)
        return

    if not issubclass(op, FullyAssociative):
        assert set(res.extracted_operands) & {A, B, C}
        assert not set(res.extracted_operands) & {D, E}
        assert len(res.destroyed_operations) == 1
        return

    assert set(res.extracted_operands) == {A, B, C, D, E}
    assert len(res.destroyed_operations) == 2


def test_mutator_no_graph_merge():
    p0 = Parameter(units=P.V)
    p1 = Parameter(units=P.A)
    p2 = Parameter(units=P.W)
    alias = p2.alias_is(p0 * p1)

    p3 = Parameter(units=P.V)

    context = ParameterOperatable.ReprContext()

    @algorithm("")
    def algo(mutator: Mutator):
        pass

    mutator = Mutator(p0.get_graph(), print_context=context, algo=algo, terminal=True)
    p0_new = cast_assert(Parameter, mutator.get_copy(p0))
    p3_new = cast_assert(Parameter, mutator.get_copy(p3))
    alias_new = cast_assert(Is, mutator.get_copy(alias))

    G = p0.get_graph()
    G_new = p0_new.get_graph()

    assert G is not G_new
    assert alias_new.get_graph() is G_new
    assert p3_new.get_graph() is not G_new
    assert cast_assert(Parameter, mutator.get_mutated(p1)).get_graph() is G_new


def test_get_expressions_involved_in():
    A = Parameter()
    B = Parameter()

    E1 = A + B

    res = get_expressions_involved_in(E1)
    assert res == set()

    E2 = E1 + A

    res = get_expressions_involved_in(E1)
    assert res == {E2}

    E3 = E2 + B

    res = get_expressions_involved_in(E1)
    assert res == {E2, E3}

    res = get_expressions_involved_in(E2)
    assert res == {E3}

    res = get_expressions_involved_in(E2, up_only=False)
    assert res == {E1, E3}

    res = get_expressions_involved_in(E2, up_only=False, include_root=True)
    assert res == {E1, E2, E3}
