from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Self, Sequence, TYPE_CHECKING, cast

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
from faebryk.library.Collections import (
    AbstractPointer,
    AbstractSequence,
    AbstractSet,
    PointerProtocol,
)
from faebryk.library.Parameters import (
    ReprContext,
    can_be_operand,
    is_parameter_operatable,
)

if TYPE_CHECKING:
    from faebryk.library import Parameters

# TODO complete signatures
# TODO consider moving to zig
# TODO handle constrained attribute

# TODO strategy with traits:
# just make everything an instance trait,
# and later when we performance optimize reconsider


# solver shims TODO remove -------------------------------------------------------------


# def _as_node(candidate: Any) -> fabll.NodeT | None:
#     if isinstance(candidate, fabll.Node):
#         return candidate
#     return None
#
#
# def isinstance_node(candidate: Any, node_type: type[fabll.NodeT]) -> bool:
#     node = _as_node(candidate)
#     if node is None:
#         return False
#     return node.isinstance(node_type)
#
#
# def isinstance_any(candidate: Any, *node_types: type[fabll.NodeT]) -> bool:
#     return any(isinstance_node(candidate, node_type) for node_type in node_types)
#
#
# def has_trait(candidate: Any, trait: type[fabll.NodeT]) -> bool:
#     node = _as_node(candidate)
#     if node is None:
#         return False
#     return node.has_trait(trait)
#
#
# def is_expression_node(candidate: Any) -> bool:
#     return has_trait(candidate, is_expression)
#
#
# def is_constrainable_node(candidate: Any) -> bool:
#     return has_trait(candidate, IsConstrainable)
#
#
# def is_canonical_expression_node(candidate: Any) -> bool:
#     node = _as_node(candidate)
#     if node is None:
#         return False
#     return node.has_trait(is_expression) and node.has_trait(is_canonical)


# --------------------------------------------------------------------------------------


def _retrieve_operands(node: fabll.NodeT, identifier: str | None) -> list[fabll.NodeT]:
    class Ctx:
        operands: list[fabll.NodeT] = []
        _identifier = identifier

    def visit(ctx: type[Ctx], edge: graph.BoundEdge):
        if ctx._identifier is not None and edge.edge().name() != ctx._identifier:
            return
        ctx.operands.append(
            fabll.Node.bind_instance(edge.g().bind(node=edge.edge().target()))
        )

    fbrk.EdgeOperand.visit_operand_edges(bound_node=node.instance, ctx=Ctx, f=visit)
    return Ctx.operands


OperandPointer = AbstractPointer(
    edge_factory=lambda identifier: fbrk.EdgeOperand.build(
        operand_identifier=identifier
    ),
    retrieval_function=lambda node: _retrieve_operands(node, None)[0],
)

OperandSequence = AbstractSequence(
    edge_factory=lambda identifier, order: fbrk.EdgeOperand.build(
        operand_identifier=identifier
    ),
    retrieval_function=_retrieve_operands,
)

OperandSet = AbstractSet(
    edge_factory=lambda identifier, order: fbrk.EdgeOperand.build(
        operand_identifier=identifier
    ),
    retrieval_function=_retrieve_operands,
)


class is_expression(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    @dataclass(frozen=True)
    class ReprStyle(fabll.NodeAttributes):
        symbol: str | None = None

        class Placement(Enum):
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
    def MakeChild(cls, repr_style: ReprStyle) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        return out

    def get_operands(self) -> list["Parameters.can_be_operand"]:
        node = fabll.Traits(self).get_obj_raw()
        operands: list[can_be_operand] = []
        pointers = node.get_children(
            direct_only=True,
            types=(OperandPointer, OperandSequence, OperandSet),  # type: ignore
        )
        for pointer in pointers:
            child = cast(PointerProtocol, pointer)
            li = child.as_list()
            assert all(c.isinstance(can_be_operand) for c in li)
            li = cast(list[can_be_operand], li)
            operands.extend(li)

        return operands

    def get_operand_operatables(self) -> set["is_parameter_operatable"]:
        return {
            po
            for op in self.get_operands()
            if (po := fabll.Traits(op).try_get_trait_of_obj(is_parameter_operatable))
        }

    @staticmethod
    def get_all_expressions_involved_in(
        node: fabll.NodeT,
    ) -> set[fabll.NodeT]:
        # 1. Find all EdgeOperand edges
        # 2. Get their source nodes
        # 3. Get their parents
        # TODO requires EdgeOperand to support multi expression edges
        raise NotImplementedError("Not implemented")

    def compact_repr(
        self, context: "ReprContext | None" = None, use_name: bool = False
    ) -> str:
        # TODO
        raise NotImplementedError()

    def as_parameter_operatable(self) -> "is_parameter_operatable":
        return fabll.Traits(self).get_trait_of_obj(is_parameter_operatable)

    def is_congruent_to_factory(
        self,
        other_factory: "type[fabll.NodeT]",
        other_operands: Sequence["Parameters.can_be_operand"],
        allow_uncorrelated: bool = False,
        # TODO
        check_constrained: bool = True,
    ) -> bool:
        # TODO
        pass

    def as_trait_of[T: fabll.NodeT](self, t: type[T]) -> T:
        return fabll.Traits(self).get_trait_of_obj(t)

    def is_trait_of[T: fabll.NodeT](self, t: type[T]) -> T | None:
        return fabll.Traits(self).try_get_trait_of_obj(t)


# TODO
class has_implicit_constraints(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class IsConstrainable(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    # TODO: solver_terminated flag, has to be attr

    def constrain(self) -> None:
        parent = self.get_parent_force()[0]
        fabll.Traits.create_and_add_instance_to(node=parent, trait=IsConstrained)

    def as_expression(self) -> "is_expression":
        return fabll.Traits(self).get_trait_of_obj(is_expression)


class IsConstrained(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


# --------------------------------------------------------------------------------------

# TODO distribute
# TODO implement functions


class is_arithmetic(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_additive(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_functional(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_logic(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_setic(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_predicate(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_numeric_predicate(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_setic_predicate(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class has_side_effects(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


# solver specific


class is_canonical(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def as_expression(self) -> "is_expression":
        return fabll.Traits(self).get_trait_of_obj(is_expression)

    def as_parameter_operatable(self) -> "Parameters.is_parameter_operatable":
        return fabll.Traits(self).get_trait_of_obj(F.Parameters.is_parameter_operatable)


# algebraic properties


class is_reflexive(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_idempotent(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class has_idempotent_operands(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_commutative(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    @classmethod
    def is_commutative_type(cls, node_type: type[fabll.NodeT]) -> bool:
        # TODO
        raise NotImplementedError


class has_unary_identity(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_fully_associative(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_associative(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_involutory(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


# --------------------------------------------------------------------------------------


class Add(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="+",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())
    _has_unary_identity = fabll.Traits.MakeEdge(has_unary_identity.MakeChild())
    _is_fully_associative = fabll.Traits.MakeEdge(is_fully_associative.MakeChild())
    _is_associative = fabll.Traits.MakeEdge(is_associative.MakeChild())

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: "Parameters.can_be_operand") -> Self:
        self.operands.get().append(*operands)
        return self


class Subtract(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="-",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    minuend = OperandPointer.MakeChild()
    subtrahends = OperandSequence.MakeChild()

    def setup(
        self,
        minuend: "Parameters.can_be_operand",
        *subtrahends: "Parameters.can_be_operand",
    ) -> Self:
        self.minuend.get().point(minuend)
        for subtrahend in subtrahends:
            self.subtrahends.get().append(subtrahend)
        return self


class Multiply(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="*",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())
    _has_unary_identity = fabll.Traits.MakeEdge(has_unary_identity.MakeChild())
    _is_fully_associative = fabll.Traits.MakeEdge(is_fully_associative.MakeChild())
    _is_associative = fabll.Traits.MakeEdge(is_associative.MakeChild())

    operands = OperandSet.MakeChild()

    def setup(self, *operands: "Parameters.can_be_operand") -> Self:
        self.operands.get().append(*operands)
        return self


class Divide(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="/",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    # denominator not zero
    _has_implicit_constraints = fabll.Traits.MakeEdge(
        has_implicit_constraints.MakeChild()
    )

    numerator = OperandPointer.MakeChild()
    denominator = OperandSequence.MakeChild()

    def setup(
        self,
        numerator: "Parameters.can_be_operand",
        *denominators: "Parameters.can_be_operand",
    ) -> Self:
        self.numerator.get().point(numerator)
        for denominator in denominators:
            self.denominator.get().append(denominator)
        return self


class Sqrt(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="√",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    # non-negative
    _has_implicit_constraints = fabll.Traits.MakeEdge(
        has_implicit_constraints.MakeChild()
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: "Parameters.can_be_operand") -> Self:
        self.operand.get().point(operand)
        return self


class Power(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="^",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())

    base = OperandPointer.MakeChild()
    exponent = OperandPointer.MakeChild()

    def setup(
        self,
        base: "Parameters.can_be_operand",
        exponent: "Parameters.can_be_operand",
    ) -> Self:
        self.base.get().point(base)
        self.exponent.get().point(exponent)
        return self


class Log(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="log",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())

    # non-negative
    _has_implicit_constraints = fabll.Traits.MakeEdge(
        has_implicit_constraints.MakeChild()
    )

    operand = OperandPointer.MakeChild()
    base = OperandPointer.MakeChild()  # Optional, defaults to natural log if not set

    def setup(
        self,
        operand: "Parameters.can_be_operand",
        base: "Parameters.can_be_operand | None" = None,
    ) -> Self:
        self.operand.get().point(operand)
        if base is not None:
            self.base.get().point(base)
        return self


class Sin(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="sin",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())

    operand = OperandPointer.MakeChild()

    def setup(self, operand: "Parameters.can_be_operand") -> Self:
        self.operand.get().point(operand)
        return self


class Cos(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="cos",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    operand = OperandPointer.MakeChild()

    def setup(self, operand: Parameters.can_be_operand) -> Self:
        self.operand.get().point(operand)
        return self


class Abs(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="|",
                placement=is_expression.ReprStyle.Placement.EMBRACE,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _is_idempotent = fabll.Traits.MakeEdge(is_idempotent.MakeChild())

    operand = OperandPointer.MakeChild()

    def setup(self, operand: Parameters.can_be_operand) -> Self:
        self.operand.get().point(operand)
        return self


class Round(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="round",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _is_idempotent = fabll.Traits.MakeEdge(is_idempotent.MakeChild())

    operand = OperandPointer.MakeChild()

    def setup(self, operand: Parameters.can_be_operand) -> Self:
        self.operand.get().point(operand)
        return self


class Floor(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="⌊",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: Parameters.can_be_operand) -> Self:
        self.operand.get().point(operand)
        return self


class Ceil(fabll.Node):
    _can_be_operand = can_be_operand.MakeChild()
    _is_parameter_operatable = is_parameter_operatable.MakeChild()
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="⌈",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: Parameters.can_be_operand) -> Self:
        self.operand.get().point(operand)
        return self


class Min(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="min",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: Parameters.can_be_operand) -> Self:
        self.operands.get().append(*operands)
        return self


class Max(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="max",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: Parameters.can_be_operand) -> Self:
        self.operands.get().append(*operands)
        return self


class Integrate(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="∫",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )

    function = OperandPointer.MakeChild()
    variable = OperandPointer.MakeChild()  # Variable to integrate with respect to

    def setup(
        self,
        operand: Parameters.can_be_operand,
        variable: Parameters.can_be_operand,
    ) -> Self:
        self.function.get().point(operand)
        self.variable.get().point(variable)
        return self


class Differentiate(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="d",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )

    function = OperandPointer.MakeChild()
    variable = OperandPointer.MakeChild()  # Variable to differentiate with respect to

    def setup(
        self,
        operand: Parameters.can_be_operand,
        variable: Parameters.can_be_operand,
    ) -> Self:
        self.function.get().point(operand)
        self.variable.get().point(variable)
        return self


class And(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="∧",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(
        self, *operands: Parameters.can_be_operand, constrain: bool = False
    ) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Or(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="∨",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _has_idempotent_operands = fabll.Traits.MakeEdge(
        has_idempotent_operands.MakeChild()
    )
    _is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())
    _has_unary_identity = fabll.Traits.MakeEdge(has_unary_identity.MakeChild())
    _is_fully_associative = fabll.Traits.MakeEdge(is_fully_associative.MakeChild())
    _is_associative = fabll.Traits.MakeEdge(is_associative.MakeChild())

    operands = OperandSequence.MakeChild()

    def setup(
        self, *operands: Parameters.can_be_operand, constrain: bool = False
    ) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Not(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="¬",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _is_involutory = fabll.Traits.MakeEdge(is_involutory.MakeChild())

    operand = OperandPointer.MakeChild()

    def setup(
        self, operand: Parameters.can_be_operand, constrain: bool = False
    ) -> Self:
        self.operand.get().point(operand)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Xor(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="⊕",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(
        self, *operands: Parameters.can_be_operand, constrain: bool = False
    ) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Implies(fabll.Node):
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="⇒",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )

    antecedent = OperandPointer.MakeChild()
    consequent = OperandPointer.MakeChild()

    def setup(
        self,
        antecedent: Parameters.can_be_operand,
        consequent: Parameters.can_be_operand,
        constrain: bool = False,
    ) -> Self:
        self.antecedent.get().point(antecedent)
        self.consequent.get().point(consequent)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class IfThenElse(fabll.Node):
    _has_side_effects = fabll.Traits.MakeEdge(has_side_effects.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="?:",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )

    condition = OperandPointer.MakeChild()
    then_value = OperandPointer.MakeChild()
    else_value = OperandPointer.MakeChild()

    def setup(
        self,
        condition: Parameters.can_be_operand,
        then_value: Parameters.can_be_operand,
        else_value: Parameters.can_be_operand,
    ) -> Self:
        self.condition.get().point(condition)
        self.then_value.get().point(then_value)
        self.else_value.get().point(else_value)
        return self


class Union(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="∪",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _has_idempotent_operands = fabll.Traits.MakeEdge(
        has_idempotent_operands.MakeChild()
    )
    _is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())
    _has_unary_identity = fabll.Traits.MakeEdge(has_unary_identity.MakeChild())
    _is_fully_associative = fabll.Traits.MakeEdge(is_fully_associative.MakeChild())
    _is_associative = fabll.Traits.MakeEdge(is_associative.MakeChild())

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: Parameters.can_be_operand) -> Self:
        self.operands.get().append(*operands)
        return self


class Intersection(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="∩",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _has_idempotent_operands = fabll.Traits.MakeEdge(
        has_idempotent_operands.MakeChild()
    )
    _is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())
    _has_unary_identity = fabll.Traits.MakeEdge(has_unary_identity.MakeChild())
    _is_fully_associative = fabll.Traits.MakeEdge(is_fully_associative.MakeChild())
    _is_associative = fabll.Traits.MakeEdge(is_associative.MakeChild())

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: Parameters.can_be_operand) -> Self:
        self.operands.get().append(*operands)
        return self


class Difference(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="−",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    minuend = OperandPointer.MakeChild()
    subtrahend = OperandPointer.MakeChild()

    def setup(
        self,
        minuend: Parameters.can_be_operand,
        subtrahend: Parameters.can_be_operand,
    ) -> Self:
        self.minuend.get().point(minuend)
        self.subtrahend.get().point(subtrahend)
        return self


class SymmetricDifference(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="△",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self,
        left: Parameters.can_be_operand,
        right: Parameters.can_be_operand,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        return self


class LessThan(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="<",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self,
        left: Parameters.can_be_operand,
        right: Parameters.can_be_operand,
        constrain: bool = False,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class GreaterThan(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol=">",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self,
        left: Parameters.can_be_operand,
        right: Parameters.can_be_operand,
        constrain: bool = False,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class LessOrEqual(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="≤",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self,
        left: Parameters.can_be_operand,
        right: Parameters.can_be_operand,
        constrain: bool = False,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class GreaterOrEqual(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="≥",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _is_reflexive = fabll.Traits.MakeEdge(is_reflexive.MakeChild())

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self,
        left: Parameters.can_be_operand,
        right: Parameters.can_be_operand,
        constrain: bool = False,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class NotEqual(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="≠",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self,
        left: Parameters.can_be_operand,
        right: Parameters.can_be_operand,
        constrain: bool = False,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class IsBitSet(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="b[]",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())

    value = OperandPointer.MakeChild()
    bit_index = OperandPointer.MakeChild()

    def setup(
        self,
        value: Parameters.can_be_operand,
        bit_index: Parameters.can_be_operand,
        constrain: bool = False,
    ) -> Self:
        self.value.get().point(value)
        self.bit_index.get().point(bit_index)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class IsSubset(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="⊆",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _is_reflexive = fabll.Traits.MakeEdge(is_reflexive.MakeChild())

    subset = OperandPointer.MakeChild()
    superset = OperandPointer.MakeChild()

    def setup(
        self,
        subset: Parameters.can_be_operand,
        superset: Parameters.can_be_operand,
        constrain: bool = False,
    ) -> Self:
        self.subset.get().point(subset)
        self.superset.get().point(superset)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class IsSuperset(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="⊇",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )

    superset = OperandPointer.MakeChild()
    subset = OperandPointer.MakeChild()

    def setup(
        self,
        superset: Parameters.can_be_operand,
        subset: Parameters.can_be_operand,
        constrain: bool = False,
    ) -> Self:
        self.superset.get().point(superset)
        self.subset.get().point(subset)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Cardinality(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="||",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )

    set = OperandPointer.MakeChild()
    cardinality = OperandPointer.MakeChild()

    def setup(
        self,
        set: Parameters.can_be_operand,
        cardinality: Parameters.can_be_operand,
        constrain: bool = False,
    ) -> Self:
        self.set.get().point(set)
        self.cardinality.get().point(cardinality)
        if constrain:
            self._is_constrainable.get().constrain()
        return self


class Is(fabll.Node):
    _can_be_operand = F.Parameters.can_be_operand.MakeChild()
    _is_parameter_operatable = F.Parameters.is_parameter_operatable.MakeChild()
    _is_reflexive = fabll.Traits.MakeEdge(is_reflexive.MakeChild())
    _is_constrainable = fabll.Traits.MakeEdge(IsConstrainable.MakeChild())
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="=",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )
    _is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    _is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())

    operands = OperandSet.MakeChild()

    def setup(self, operands: list[Parameters.can_be_operand], constrain: bool) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def MakeChild_Constrain(
        cls, operands: list[fabll.RefPath]
    ) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        out.add_dependant(IsConstrained.MakeChild(), identifier="constrain")
        out.add_dependant(
            *OperandSet.MakeEdges([out, cls.operands], operands),
            identifier="connect_operands",
        )
        return out
