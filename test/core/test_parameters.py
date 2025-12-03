# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import cast

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


def test_new_definitions():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    literals = F.Literals.BoundLiteralContext(tg, g)
    parameters = F.Parameters.BoundParameterContext(tg, g)
    number_domain = F.NumberDomain.BoundNumberDomainContext(tg, g)

    parameters.NumericParameter.setup(
        units=F.Units.Ohm,
        domain=number_domain.create_number_domain(
            args=F.NumberDomain.Args(negative=False)
        ),
        soft_set=literals.Numbers.setup_from_interval(1, 10e6, F.Units.Ohm),
        likely_constrained=True,
    )


def test_compact_repr():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    p1 = (
        F.Parameters.NumericParameter.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(units=F.Units.Volt)
    )
    p2 = (
        F.Parameters.NumericParameter.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(units=F.Units.Volt)
    )
    context = F.Parameters.ReprContext()
    expr = cast(Expression, (p1 + p2 + (5 * P.V)) * 10)  # type: ignore
    exprstr = expr.compact_repr(context)
    assert exprstr == "((A volt + B volt) + 5 volt) * 10"
    expr2 = p2 + p1
    expr2str = expr2.compact_repr(context)
    assert expr2str == "B volt + A volt"

    p3 = Parameter(domain=fabll.Domains.BOOL())
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


@pytest.mark.xfail(reason="TODO is_congruent_to not implemeneted yet")
def test_expression_congruence():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    parameters = F.Parameters.BoundParameterContext(tg, g)

    p1 = parameters.NumericParameter
    p2 = parameters.NumericParameter
    p3 = parameters.NumericParameter

    assert (
        F.Expressions.Add.bind_typegraph(tg)
        .create_instance(g)
        .setup(p1, p2)
        .get_trait(F.Expressions.is_expression)
        .is_congruent_to(
            F.Expressions.Add.bind_typegraph(tg).create_instance(g).setup(p1, p2),
            g=g,
            tg=tg,
        )
    )
    assert (
        F.Expressions.Add.bind_typegraph(tg)
        .create_instance(g)
        .setup(p1, p2)
        .get_trait(F.Expressions.is_expression)
        .is_congruent_to(
            F.Expressions.Add.bind_typegraph(tg).create_instance(g).setup(p2, p1),
            g=g,
            tg=tg,
        )
    )

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


@pytest.mark.xfail(reason="TODO is_congruent_to not implemeneted yet")
def test_expression_congruence_not():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    A = F.Parameters.NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)
    x = Is(A, EnumSet(F.LED.Color.EMERALD))
    assert x.is_congruent_to(Is(A, EnumSet(F.LED.Color.EMERALD)))
    assert Not(x).is_congruent_to(Not(x))


if __name__ == "__main__":
    # test_enums()
    test_enum_param()
