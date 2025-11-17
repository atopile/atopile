# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import cast

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


def _test_new_definitions():
    _ = Parameter(
        units=P.ohm,
        domain=fabll.Domains.Numbers.REAL(negative=False),
        soft_set=fabll.Range(1 * P.ohm, 10 * P.Mohm),
        likely_constrained=True,
    )


def _test_compact_repr():
    p1 = Parameter(units=P.V)
    p2 = Parameter(units=P.V)
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


def _test_expression_congruence():
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


def _test_expression_congruence_not():
    A = Parameter()
    x = Is(A, EnumSet(F.LED.Color.EMERALD))
    assert x.is_congruent_to(Is(A, EnumSet(F.LED.Color.EMERALD)))
    assert Not(x).is_congruent_to(Not(x))


def test_string_param():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    import faebryk.library._F as F

    string_p = F.Parameters.StringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    string_p.constrain_to_single(value="IG constrained")
    assert string_p.force_extract_literal().get_value() == "IG constrained"

    class ExampleStringParameter(fabll.Node):
        string_p_tg = F.Parameters.StringParameter.MakeChild()
        constraint = F.Literals.Strings.MakeChild_ConstrainToLiteral(
            [string_p_tg], "TG constrained"
        )

    esp = ExampleStringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert esp.string_p_tg.get().force_extract_literal().get_value() == "TG constrained"


def test_boolean_param():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    import faebryk.library._F as F

    boolean_p = F.Parameters.BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    boolean_p.constrain_to_single(value=True)
    assert boolean_p.force_extract_literal().get_value()

    class ExampleBooleanParameter(fabll.Node):
        boolean_p_tg = F.Parameters.BooleanParameter.MakeChild()
        constraint = F.Literals.Booleans.MakeChild_ConstrainToLiteral(
            [boolean_p_tg], True
        )

    ebp = ExampleBooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert ebp.boolean_p_tg.get().force_extract_literal().get_value()


def test_make_lit():
    import faebryk.library._F as F

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    assert F.Literals.make_lit(tg, value=True).get_value()
    assert F.Literals.make_lit(tg, value=3).get_value() == 3
    assert F.Literals.make_lit(tg, value="test").get_value() == "test"


if __name__ == "__main__":
    test_boolean_param()
