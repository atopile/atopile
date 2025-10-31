from dataclasses import dataclass
from enum import auto
from typing import Any, Self, cast

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.zig.gen.faebryk.operand import EdgeOperand
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundEdge, GraphView

# TODO complete signatures
# TODO consider moving to zig
# TODO handle constrained attribute


def _retrieve_operands(
    node: fabll.Node[Any], identifier: str | None
) -> list[fabll.Node[Any]]:
    class Ctx:
        operands: list[fabll.Node[Any]] = []
        _identifier = identifier

    def visit(ctx: type[Ctx], edge: BoundEdge):
        if ctx._identifier is not None and edge.edge().name() != ctx._identifier:
            return
        ctx.operands.append(
            fabll.Node[Any].bind_instance(edge.g().bind(node=edge.edge().target()))
        )

    EdgeOperand.visit_operand_edges(bound_node=node.instance, ctx=Ctx, f=visit)
    return Ctx.operands


OperandPointer = F.Collections.AbstractPointer(
    edge_factory=lambda identifier: EdgeOperand.build(operand_identifier=identifier),
    retrieval_function=lambda node: _retrieve_operands(node, None)[0],
)

OperandSequence = F.Collections.AbstractSequence(
    edge_factory=lambda identifier, order: EdgeOperand.build(
        operand_identifier=identifier
    ),
    retrieval_function=_retrieve_operands,
)

OperandSet = F.Collections.AbstractSet(
    edge_factory=lambda identifier, order: EdgeOperand.build(
        operand_identifier=identifier
    ),
    retrieval_function=_retrieve_operands,
)


class IsExpression(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    @dataclass(frozen=True)
    class ReprStyle(fabll.NodeAttributes):
        symbol: str | None = None

        class Placement(fabll.Enum):
            INFIX = auto()
            """
            A + B + C
            """
            INFIX_FIRST = auto()
            """
            A > (B, C)
            """
            PREFIX = auto()
            """
            ¬A
            """
            POSTFIX = auto()
            """
            A!
            """
            EMBRACE = auto()
            """
            |A|
            """

        placement: Placement = Placement.INFIX

    @classmethod
    def MakeChild(cls, repr_style: ReprStyle) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        return out

    @staticmethod
    def get_all_operands(node: fabll.Node[Any]) -> set[fabll.Node[Any]]:
        operands: set[fabll.Node[Any]] = set()
        for child in node.get_children(
            direct_only=True,
            types=(OperandPointer, OperandSequence, OperandSet),  # type: ignore
        ):
            child = cast(F.Collections.PointerProtocol, child)
            operands.update(child.as_list())

        return operands

    @staticmethod
    def get_all_expressions_involved_in(node: fabll.Node[Any]) -> set[fabll.Node[Any]]:
        # 1. Find all EdgeOperand edges
        # 2. Get their source nodes
        # 3. Get their parents
        # TODO requires EdgeOperand to support multi expression edges
        raise NotImplementedError("Not implemented")


# --------------------------------------------------------------------------------------


class Add(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="+",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: fabll.Node[Any]) -> Self:
        self.operands.get().append(*operands)
        return self


class Subtract(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="-",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )

    minuend = OperandPointer.MakeChild()
    subtrahends = OperandSequence.MakeChild()

    def get_minuend(self) -> fabll.Node[Any]:
        return self.minuend.get().deref()

    def get_subtrahends(self) -> set[fabll.Node[Any]]:
        return self.subtrahends.get().as_set()

    def setup(self, minuend: fabll.Node[Any], *subtrahends: fabll.Node[Any]) -> Self:
        self.minuend.get().point(minuend)
        for subtrahend in subtrahends:
            self.subtrahends.get().append(subtrahend)
        return self


class Multiply(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="*",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )

    operands = OperandSet.MakeChild()

    def setup(self, *operands: fabll.Node[Any]) -> Self:
        self.operands.get().append(*operands)
        return self


class Divide(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="/",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )

    numerator = OperandPointer.MakeChild()
    denominator = OperandSequence.MakeChild()

    def get_numerator(self) -> fabll.Node[Any]:
        return self.numerator.get().deref()

    def get_denominator(self) -> set[fabll.Node[Any]]:
        return self.denominator.get().as_set()

    def setup(self, numerator: fabll.Node[Any], *denominators: fabll.Node[Any]) -> Self:
        self.numerator.get().point(numerator)
        for denominator in denominators:
            self.denominator.get().append(denominator)
        return self


class Sqrt(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="√",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Power(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="^",
            placement=IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class Log(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="log",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Sin(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="sin",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Cos(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="cos",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Abs(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="|",
            placement=IsExpression.ReprStyle.Placement.EMBRACE,
        )
    )


class Round(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="round",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Floor(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="⌊",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Ceil(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="⌈",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Min(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="min",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Max(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="max",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Integrate(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="∫",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Differentiate(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="d",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class And(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="∧",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Or(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="∨",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Not(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="¬",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Xor(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="⊕",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Implies(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="⇒",
            placement=IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class IfThenElse(fabll.Node):
    pass


class Union(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="∪",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Intersection(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="∩",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class Difference(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="−",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class SymmetricDifference(fabll.Node):
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="△",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class LessThan(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="<",
            placement=IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class GreaterThan(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol=">",
            placement=IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class LessOrEqual(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="≤",
            placement=IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class GreaterOrEqual(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="≥",
            placement=IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class NotEqual(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="≠",
            placement=IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class IsBitSet(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="b[]",
            placement=IsExpression.ReprStyle.Placement.INFIX,
        )
    )


class IsSubset(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="⊆",
            placement=IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class IsSuperset(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="⊇",
            placement=IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )


class Cardinality(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="||",
            placement=IsExpression.ReprStyle.Placement.PREFIX,
        )
    )


class Is(fabll.Node):
    _is_constrainable = fabll.IsConstrainable.MakeChild()
    _is_expression = IsExpression.MakeChild(
        repr_style=IsExpression.ReprStyle(
            symbol="=",
            placement=IsExpression.ReprStyle.Placement.INFIX_FIRST,
        )
    )

    operands = OperandSet.MakeChild()

    def setup(self, operands: list[fabll.Node[Any]], constrain: bool) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def MakeChild_Constrain(
        cls, operands: list[fabll.RefPath]
    ) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        out.add_dependant(fabll.IsConstrained.MakeChild())
        out.add_dependant(*OperandSet.EdgeFields([out, cls.operands], operands))
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
