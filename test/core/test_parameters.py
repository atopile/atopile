# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import pairwise
from typing import cast

import pytest

import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.core.parameter import (
    Add,
    Additive,
    And,
    Expression,
    Is,
    Not,
    Parameter,
    ParameterOperatable,
)
from faebryk.libs.library import L
from faebryk.libs.library.L import Range
from faebryk.libs.sets.quantity_sets import Quantity_Interval, Quantity_Singleton
from faebryk.libs.sets.sets import BoolSet, EnumSet
from faebryk.libs.units import P
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


def test_new_definitions():
    _ = Parameter(
        units=P.ohm,
        domain=L.Domains.Numbers.REAL(negative=False),
        soft_set=Range(1 * P.ohm, 10 * P.Mohm),
        likely_constrained=True,
    )


def test_compact_repr():
    p1 = Parameter(units=P.V)
    p2 = Parameter(units=P.V)
    context = ParameterOperatable.ReprContext()
    expr = cast(Expression, (p1 + p2 + (5 * P.V)) * 10)  # type: ignore
    exprstr = expr.compact_repr(context)
    assert exprstr == "((A volt + B volt) + 5 volt) * 10"
    expr2 = p2 + p1
    expr2str = expr2.compact_repr(context)
    assert expr2str == "B volt + A volt"

    p3 = Parameter(domain=L.Domains.BOOL())
    expr3 = Not(p3)
    expr3str = expr3.compact_repr(context)
    assert expr3str == "¬C"

    expr4 = And(expr3, (expr >= 10 * P.V))
    expr4str = expr4.compact_repr(context)
    assert expr4str == "¬C ∧ ((((A volt + B volt) + 5 volt) * 10) ≥ 10 volt)"

    manyps = times(ord("Z") - ord("C") - 1, Parameter)
    Additive.sum(manyps).compact_repr(context)

    pZ = Parameter()
    assert pZ.compact_repr(context) == "Z"

    pa = Parameter()
    assert pa.compact_repr(context) == "a"

    manyps2 = times(ord("z") - ord("a"), Parameter)
    Additive.sum(manyps2).compact_repr(context)
    palpha = Parameter()
    assert palpha.compact_repr(context) == "α"
    pbeta = Parameter()
    assert pbeta.compact_repr(context) == "β"

    manyps3 = times(ord("ω") - ord("β"), Parameter)
    Additive.sum(manyps3).compact_repr(context)
    pAA = Parameter()
    assert pAA.compact_repr(context) == "A₁"


def test_expression_congruence():
    p1 = Parameter()
    p2 = Parameter()
    p3 = Parameter()
    assert (p1 + p2).is_congruent_to(p1 + p2)
    assert (p1 + p2).is_congruent_to(p2 + p1)

    assert hash(Quantity_Singleton(0)) == hash(Quantity_Singleton(0))
    assert Quantity_Singleton(0) == Quantity_Singleton(0)
    assert Add(Quantity_Singleton(0), p2, p1).is_congruent_to(
        Add(p1, p2, Quantity_Singleton(0))
    )

    assert Add(Quantity_Interval(0, 1)).is_congruent_to(
        Add(Quantity_Interval(0, 1)), allow_uncorrelated=True
    )
    assert not (p1 - p2).is_congruent_to(p2 - p1)

    assert Is(p1, p2).is_congruent_to(Is(p2, p1))
    assert Is(p1, BoolSet(True)).is_congruent_to(Is(BoolSet(True), p1))
    p3.alias_is(p2)
    assert not Is(p1, p3).is_congruent_to(Is(p1, p2))


def test_expression_congruence_not():
    A = Parameter()
    x = Is(A, EnumSet(F.LED.Color.EMERALD))
    assert x.is_congruent_to(Is(A, EnumSet(F.LED.Color.EMERALD)))
    assert Not(x).is_congruent_to(Not(x))


@pytest.mark.skip
def test_visualize():
    """
    Creates webserver that opens automatically if run in jupyter notebook
    """
    from faebryk.exporters.visualize.interactive_params import visualize_parameters

    class App(Node):
        p1 = L.f_field(Parameter)(units=P.V)

    app = App()

    p2 = Parameter(units=P.V)
    p3 = Parameter(units=P.A)

    # app.p1.constrain_ge(p2 * 5)
    # app.p1.operation_is_ge(p2 * 5).constrain()
    (app.p1 >= p2 * 5).constrain()

    (p2 * p3 + app.p1 * 1 * P.A <= 10 * P.W).constrain()

    pytest.raises(ValueError, bool, app.p1 >= p2 * 5)

    G = app.get_graph()
    visualize_parameters(G, height=1400)


@pytest.mark.skip
def test_visualize_chain():
    from faebryk.exporters.visualize.interactive_params import visualize_parameters

    params = times(10, Parameter)
    sums = [p1 + p2 for p1, p2 in pairwise(params)]
    products = [p1 * p2 for p1, p2 in pairwise(sums)]
    bigsum = Additive.sum(products)

    predicates = [bigsum <= 100]
    for p in predicates:
        p.constrain()

    G = params[0].get_graph()
    visualize_parameters(G, height=1400)


@pytest.mark.skip
def test_visualize_inspect_app():
    from faebryk.exporters.visualize.interactive_params import visualize_parameters

    rp2040 = F.RP2040()

    G = rp2040.get_graph()
    visualize_parameters(G, height=1400)
