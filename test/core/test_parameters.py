# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import cast

import pytest
from shapely import force_2d

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none, times

logger = logging.getLogger(__name__)


def test_new_definitions():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    literals = F.Literals.BoundLiteralContext(tg, g)
    parameters = F.Parameters.BoundParameterContext(tg, g)
    number_domain = F.NumberDomain.BoundNumberDomainContext(tg, g)

    parameters.create_numeric_parameter(
        units=F.Units.Ohm._is_unit.get(),
        domain=number_domain.create_number_domain(negative=False),
        soft_set=literals.create_numbers_from_interval(
            1, 10e6, F.Units.Ohm._is_unit.get()
        ),
        likely_constrained=True,
    )


def test_compact_repr():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    p1 = (
        F.Parameters.NumericParameter.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(units=F.Units.Volt._is_unit.get())
    )
    p2 = (
        F.Parameters.NumericParameter.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(units=F.Units.Volt._is_unit.get())
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

    p1 = parameters.create_numeric_parameter()
    p2 = parameters.create_numeric_parameter()
    p3 = parameters.create_numeric_parameter()

    assert (
        F.Expressions.Add.bind_typegraph(tg)
        .create_instance(g)
        .setup(p1, p2)
        .get_trait(F.Expressions.is_expression)
        .is_congruent_to(
            F.Expressions.Add.bind_typegraph(tg).create_instance(g).setup(p1, p2)
        )
    )
    assert (
        F.Expressions.Add.bind_typegraph(tg)
        .create_instance(g)
        .setup(p1, p2)
        .get_trait(F.Expressions.is_expression)
        .is_congruent_to(
            F.Expressions.Add.bind_typegraph(tg).create_instance(g).setup(p2, p1)
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


def test_string_param():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    import faebryk.library._F as F

    string_p = F.Parameters.StringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    string_p.alias_to_literal("IG constrained")
    assert string_p.force_extract_literal().get_value() == "IG constrained"

    class ExampleStringParameter(fabll.Node):
        string_p_tg = F.Parameters.StringParameter.MakeChild()
        constraint = F.Literals.Strings.MakeChild_ConstrainToLiteral(
            [string_p_tg], "TG constrained"
        )

    esp = ExampleStringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert esp.string_p_tg.get().force_extract_literal().get_value() == "TG constrained"


def test_boolean_param():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    import faebryk.library._F as F

    boolean_p = F.Parameters.BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    boolean_p.alias_to_single(value=True, g=g)
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

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    assert F.Literals.make_lit(tg, value=True).get_value()
    assert F.Literals.make_lit(tg, value=3).get_value() == 3
    assert F.Literals.make_lit(tg, value="test").get_value() == "test"


def test_enum_param():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    from enum import Enum

    import faebryk.library._F as F

    # F.Resistor.bind_typegraph(tg=tg).get_or_create_type()

    class ExampleNode(fabll.Node):
        class MyEnum(Enum):
            A = "a"
            B = "b"
            C = "c"
            D = "d"

        enum_p_tg = F.Parameters.EnumParameter.MakeChild(enum_t=MyEnum)
        constraint = F.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
            [enum_p_tg], MyEnum.B, MyEnum.C
        )

        # ptr = F.Collections.Pointer.MakeChild()
        # constraint = F.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
        #     [F.Resistor], MyEnum.B, MyEnum.C
        # )
        _has_usage_example = F.has_usage_example.MakeChild(
            example="",
            language=F.has_usage_example.Language.ato,
        ).put_on_type()

    example_node = ExampleNode.bind_typegraph(tg=tg).create_instance(g=g)

    # Enum Literal Type Node
    atype = F.Literals.EnumsFactory(ExampleNode.MyEnum)
    cls_n = cast(type[fabll.NodeT], atype)
    enum_type_node = cls_n.bind_typegraph(tg=tg).get_or_create_type()

    # Enum Parameter from TG
    enum_param = example_node.enum_p_tg.get()

    abstract_enum_type_node = enum_param.get_enum_type()
    # assert abstract_enum_type_node.is_same(enum_type_node)

    assert [(m.name, m.value) for m in abstract_enum_type_node.get_all_members()] == [
        (m.name, m.value) for m in ExampleNode.MyEnum
    ]

    assert abstract_enum_type_node.get_enum_as_dict() == {
        m.name: m.value for m in ExampleNode.MyEnum
    }

    enum_lit = enum_param.force_extract_literal()
    assert enum_lit.get_values() == ["b", "c"]

    # Enum Parameter from instance graph
    enum_p_ig = F.Parameters.EnumParameter.bind_typegraph(tg=tg).create_instance(g=g)
    enum_p_ig.alias_to_literal(ExampleNode.MyEnum.B, g=g)
    assert enum_p_ig.force_extract_literal().get_values() == ["b"]


def test_enums():
    """
    Tests carried over from enum_sets.py
    """
    from enum import Enum

    import faebryk.library._F as F
    from faebryk.core.node import _make_graph_and_typegraph

    g, tg = _make_graph_and_typegraph()

    class MyEnum(Enum):
        A = "a"
        D = "d"

    EnumT = F.Literals.EnumsFactory(MyEnum)
    enum_lit = EnumT.bind_typegraph(tg=tg).create_instance(g=g)

    elements = enum_lit.get_all_members()
    assert len(elements) == 2
    assert elements[0].name == "A"
    assert elements[0].value == MyEnum.A.value
    assert elements[1].name == "D"
    assert elements[1].value == MyEnum.D.value


if __name__ == "__main__":
    # test_enums()
    test_enum_param()
