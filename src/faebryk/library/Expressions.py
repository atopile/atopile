from typing import Any, Self

import faebryk.core.node as fabll
from faebryk.core.zig.gen.faebryk.operand import EdgeOperand
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import GraphView

# TODO complete signatures
# TODO consider moving to zig
# TODO handle constrained attribute
# TODO consider EdgeOperand vs Operand Nodes + Pointer


class Add(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="+",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Subtract(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="-",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Multiply(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="*",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Divide(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="/",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Sqrt(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="√",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Power(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="^",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class Log(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="log",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Sin(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="sin",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Cos(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="cos",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Abs(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="|",
            placement=fabll.IsExpression.ReprStyle.Placement.EMBRACE,
        )
    )


class Round(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="round",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Floor(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="⌊",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Ceil(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="⌈",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Min(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="min",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Max(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="max",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Integrate(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="∫",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Differentiate(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="d",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class And(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="∧",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Or(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="∨",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Not(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="¬",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Xor(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="⊕",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Implies(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="⇒",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class IfThenElse(fabll.Node):
    pass


class Union(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="∪",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Intersection(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="∩",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Difference(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="−",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class SymmetricDifference(fabll.Node):
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="△",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class LessThan(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="<",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class GreaterThan(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol=">",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class LessOrEqual(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="≤",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class GreaterOrEqual(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="≥",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class NotEqual(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="≠",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class IsBitSet(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="b[]",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class IsSubset(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="⊆",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class IsSuperset(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="⊇",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class Cardinality(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="||",
            placement=fabll.IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Is(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = fabll.IsExpression.MakeChild(
        repr_style=fabll.IsExpression.ReprStyle(
            symbol="=",
            placement=fabll.IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )

    @classmethod
    def constrain_is(
        cls, tg: TypeGraph, g: GraphView, operands: list[fabll.Node[Any]]
    ) -> Self:
        out = cls.bind_typegraph(tg).create_instance(g=g)
        for operand in operands:
            out.connect(
                to=operand,
                edge_attrs=EdgeOperand.build(operand_identifier=None),
            )
        return out

    @classmethod
    def MakeChild_Constrain(
        cls, operands: list[fabll.RefPath]
    ) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        out.add_dependant(fabll.IsConstrained.MakeChild())
        for operand in operands:
            edge = fabll.EdgeField(
                [out],
                operand,
                edge=EdgeOperand.build(operand_identifier=None),
            )
            out.add_dependant(edge)
        return out

    @classmethod
    def MakeChild_ConstrainToLiteral(
        cls,
        ref: list[str | fabll.ChildField[Any]],
        value: fabll.LiteralT,
    ) -> fabll.ChildField[Any]:
        lit = fabll.ChildField(
            fabll.LiteralNode,
            attributes=fabll.LiteralNodeAttributes(value=value),
        )
        out = cls.MakeChild_Constrain([ref, [lit]])
        out.add_dependant(lit)
        return out
