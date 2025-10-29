from typing import Any

import faebryk.core.node as fabll
from faebryk.core.zig.gen.faebryk.operand import EdgeOperand
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundNode, GraphView

# TODO complete signatures
# TODO consider moving to zig
# TODO handle constrained attribute


class Add(fabll.Node):
    pass


class Subtract(fabll.Node):
    pass


class Multiply(fabll.Node):
    pass


class Divide(fabll.Node):
    pass


class Sqrt(fabll.Node):
    pass


class Power(fabll.Node):
    pass


class Log(fabll.Node):
    pass


class Sin(fabll.Node):
    pass


class Cos(fabll.Node):
    pass


class Abs(fabll.Node):
    pass


class Round(fabll.Node):
    pass


class Floor(fabll.Node):
    pass


class Ceil(fabll.Node):
    pass


class Min(fabll.Node):
    pass


class Max(fabll.Node):
    pass


class Integrate(fabll.Node):
    pass


class Differentiate(fabll.Node):
    pass


class And(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class Or(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class Not(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class Xor(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class Implies(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class IfThenElse(fabll.Node):
    pass


class Union(fabll.Node):
    pass


class Intersection(fabll.Node):
    pass


class Difference(fabll.Node):
    pass


class SymmetricDifference(fabll.Node):
    pass


class LessThan(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class GreaterThan(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class LessOrEqual(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class GreaterOrEqual(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class NotEqual(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class IsBitSet(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class IsSubset(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class IsSuperset(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class Cardinality(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()


class Is(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()

    @classmethod
    def constrain_is(
        cls, tg: TypeGraph, g: GraphView, operands: list[BoundNode]
    ) -> BoundNode:
        # TODO
        raise NotImplementedError()

    @classmethod
    def MakeChild_ConstrainToLiteral(
        cls,
        ref: list[str | fabll.ChildField[Any]],
        value: fabll.LiteralT,
    ) -> fabll.ChildField[Any]:
        alias = fabll.ChildField(cls)
        constrained = fabll.IsConstrained.MakeChild()
        alias.add_dependant(constrained)
        lit = fabll.ChildField(
            fabll.LiteralNode,
            attributes=fabll.LiteralNodeAttributes(value=value),
        )
        alias_edge = fabll.EdgeField(
            ref,
            [lit],
            edge=EdgeOperand.build(operand_identifier=None),
        )
        alias.add_dependant(alias_edge)
        alias.add_dependant(lit)
        return alias
