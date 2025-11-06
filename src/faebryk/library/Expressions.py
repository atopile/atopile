from dataclasses import dataclass
from enum import auto
from typing import Any, Self, cast

import faebryk.core.node as fabll
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
import faebryk.library._F as F
from faebryk.core.zig.gen.faebryk.operand import EdgeOperand
from faebryk.core.zig.gen.graph.graph import BoundEdge

# TODO complete signatures
# TODO consider moving to zig
# TODO handle constrained attribute

# TODO strategy with traits:
# just make everything an instance trait,
# and later when we performance optimize reconsider


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


class is_expression(fabll.Node):
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


# TODO
class has_implicit_constraints(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class IsConstrainable(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    def constrain(self) -> None:
        parent = self.get_parent_force()[0]
        fabll.Traits.create_and_add_instance_to(node=parent, trait=IsConstrained)


class IsConstrained(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


# --------------------------------------------------------------------------------------

# TODO distribute
# TODO implement functions


class is_arithmetic(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class is_additive(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class is_functional(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class is_logic(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class is_setic(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class is_predicate(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class is_numeric_predicate(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class is_setic_predicate(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


# --------------------------------------------------------------------------------------


class Add(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="+",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: fabll.Node[Any]) -> Self:
        self.operands.get().append(*operands)
        return self


class Subtract(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="-",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    minuend = OperandPointer.MakeChild()
    subtrahends = OperandSequence.MakeChild()

    def setup(self, minuend: fabll.Node[Any], *subtrahends: fabll.Node[Any]) -> Self:
        self.minuend.get().point(minuend)
        for subtrahend in subtrahends:
            self.subtrahends.get().append(subtrahend)
        return self


class Multiply(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="*",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    operands = OperandSet.MakeChild()

    def setup(self, *operands: fabll.Node[Any]) -> Self:
        self.operands.get().append(*operands)
        return self


class Divide(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="/",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )
    # denominator not zero
    _has_implicit_constraints = has_implicit_constraints.MakeChild()

    numerator = OperandPointer.MakeChild()
    denominator = OperandSequence.MakeChild()

    def setup(self, numerator: fabll.Node[Any], *denominators: fabll.Node[Any]) -> Self:
        self.numerator.get().point(numerator)
        for denominator in denominators:
            self.denominator.get().append(denominator)
        return self


class Sqrt(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="√",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )
    # non-negative
    _has_implicit_constraints = has_implicit_constraints.MakeChild()

    operand = OperandPointer.MakeChild()

    def setup(self, operand: fabll.Node[Any]) -> Self:
        self.operand.get().point(operand)
        return self


class Power(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="^",
            placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
        )
    )

    base = OperandPointer.MakeChild()
    exponent = OperandPointer.MakeChild()

    def setup(self, base: fabll.Node[Any], exponent: fabll.Node[Any]) -> Self:
        self.base.get().point(base)
        self.exponent.get().point(exponent)
        return self


class Log(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="log",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    # non-negative
    _has_implicit_constraints = has_implicit_constraints.MakeChild()

    operand = OperandPointer.MakeChild()
    base = OperandPointer.MakeChild()  # Optional, defaults to natural log if not set

    def setup(
        self, operand: fabll.Node[Any], base: fabll.Node[Any] | None = None
    ) -> Self:
        self.operand.get().point(operand)
        if base is not None:
            self.base.get().point(base)
        return self


class Sin(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="sin",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: fabll.Node[Any]) -> Self:
        self.operand.get().point(operand)
        return self


class Cos(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="cos",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: fabll.Node[Any]) -> Self:
        self.operand.get().point(operand)
        return self


class Abs(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="|",
            placement=is_expression.ReprStyle.Placement.EMBRACE,
        )
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: fabll.Node[Any]) -> Self:
        self.operand.get().point(operand)
        return self


class Round(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="round",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: fabll.Node[Any]) -> Self:
        self.operand.get().point(operand)
        return self


class Floor(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="⌊",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: fabll.Node[Any]) -> Self:
        self.operand.get().point(operand)
        return self


class Ceil(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="⌈",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: fabll.Node[Any]) -> Self:
        self.operand.get().point(operand)
        return self


class Min(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="min",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: fabll.Node[Any]) -> Self:
        self.operands.get().append(*operands)
        return self


class Max(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="max",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: fabll.Node[Any]) -> Self:
        self.operands.get().append(*operands)
        return self


class Integrate(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="∫",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    function = OperandPointer.MakeChild()
    variable = OperandPointer.MakeChild()  # Variable to integrate with respect to

    def setup(self, operand: fabll.Node[Any], variable: fabll.Node[Any]) -> Self:
        self.function.get().point(operand)
        self.variable.get().point(variable)
        return self


class Differentiate(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="d",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    function = OperandPointer.MakeChild()
    variable = OperandPointer.MakeChild()  # Variable to differentiate with respect to

    def setup(self, operand: fabll.Node[Any], variable: fabll.Node[Any]) -> Self:
        self.function.get().point(operand)
        self.variable.get().point(variable)
        return self


class And(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="∧",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: fabll.Node[Any], constrain: bool = False) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Or(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="∨",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: fabll.Node[Any], constrain: bool = False) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Not(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="¬",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: fabll.Node[Any], constrain: bool = False) -> Self:
        self.operand.get().point(operand)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Xor(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="⊕",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: fabll.Node[Any], constrain: bool = False) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Implies(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="⇒",
            placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
        )
    )

    antecedent = OperandPointer.MakeChild()
    consequent = OperandPointer.MakeChild()

    def setup(
        self,
        antecedent: fabll.Node[Any],
        consequent: fabll.Node[Any],
        constrain: bool = False,
    ) -> Self:
        self.antecedent.get().point(antecedent)
        self.consequent.get().point(consequent)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class IfThenElse(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="?:",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    condition = OperandPointer.MakeChild()
    then_value = OperandPointer.MakeChild()
    else_value = OperandPointer.MakeChild()

    def setup(
        self,
        condition: fabll.Node[Any],
        then_value: fabll.Node[Any],
        else_value: fabll.Node[Any],
    ) -> Self:
        self.condition.get().point(condition)
        self.then_value.get().point(then_value)
        self.else_value.get().point(else_value)
        return self


class Union(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="∪",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: fabll.Node[Any]) -> Self:
        self.operands.get().append(*operands)
        return self


class Intersection(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="∩",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: fabll.Node[Any]) -> Self:
        self.operands.get().append(*operands)
        return self


class Difference(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="−",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    minuend = OperandPointer.MakeChild()
    subtrahend = OperandPointer.MakeChild()

    def setup(self, minuend: fabll.Node[Any], subtrahend: fabll.Node[Any]) -> Self:
        self.minuend.get().point(minuend)
        self.subtrahend.get().point(subtrahend)
        return self


class SymmetricDifference(fabll.Node):
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="△",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(self, left: fabll.Node[Any], right: fabll.Node[Any]) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        return self


class LessThan(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="<",
            placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
        )
    )

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self, left: fabll.Node[Any], right: fabll.Node[Any], constrain: bool = False
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class GreaterThan(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol=">",
            placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
        )
    )

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self, left: fabll.Node[Any], right: fabll.Node[Any], constrain: bool = False
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class LessOrEqual(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="≤",
            placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
        )
    )

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self, left: fabll.Node[Any], right: fabll.Node[Any], constrain: bool = False
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class GreaterOrEqual(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="≥",
            placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
        )
    )

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self, left: fabll.Node[Any], right: fabll.Node[Any], constrain: bool = False
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class NotEqual(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="≠",
            placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
        )
    )

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self, left: fabll.Node[Any], right: fabll.Node[Any], constrain: bool = False
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class IsBitSet(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="b[]",
            placement=is_expression.ReprStyle.Placement.INFIX,
        )
    )

    value = OperandPointer.MakeChild()
    bit_index = OperandPointer.MakeChild()

    def setup(
        self,
        value: fabll.Node[Any],
        bit_index: fabll.Node[Any],
        constrain: bool = False,
    ) -> Self:
        self.value.get().point(value)
        self.bit_index.get().point(bit_index)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class IsSubset(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="⊆",
            placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
        )
    )

    subset = OperandPointer.MakeChild()
    superset = OperandPointer.MakeChild()

    def setup(
        self,
        subset: fabll.Node[Any],
        superset: fabll.Node[Any],
        constrain: bool = False,
    ) -> Self:
        self.subset.get().point(subset)
        self.superset.get().point(superset)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class IsSuperset(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="⊇",
            placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
        )
    )

    superset = OperandPointer.MakeChild()
    subset = OperandPointer.MakeChild()

    def setup(
        self,
        superset: fabll.Node[Any],
        subset: fabll.Node[Any],
        constrain: bool = False,
    ) -> Self:
        self.superset.get().point(superset)
        self.subset.get().point(subset)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Cardinality(fabll.Node):
    _is_constrainable = IsConstrainable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="||",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    set = OperandPointer.MakeChild()
    cardinality = OperandPointer.MakeChild()

    def setup(
        self,
        set: fabll.Node[Any],
        cardinality: fabll.Node[Any],
        constrain: bool = False,
    ) -> Self:
        self.set.get().point(set)
        self.cardinality.get().point(cardinality)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Is(fabll.Node):
    _is_constrainable = fabll.ChildField(IsConstrainable)
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="=",
            placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
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
        out.add_dependant(IsConstrained.MakeChild(), identifier="constrain")
        out.add_dependant(
            *OperandSet.EdgeFields([out, cls.operands], operands),
            identifier="connect_operands",
        )
        return out

    @classmethod
    def MakeChild_ConstrainToLiteral(
        cls,
        ref: list[str | fabll.ChildField[Any]],
        value: fabll.LiteralT,
    ) -> fabll.ChildField[Any]:
        lit = fabll.LiteralNode.MakeChild(value=value)
        out = cls.MakeChild_Constrain([ref, [lit]])
        out.add_dependant(lit, identifier="lit", before=True)
        return out
