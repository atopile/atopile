from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Iterable, Self, Sequence, cast

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
from faebryk.library import Collections, Literals, Parameters
from faebryk.libs.util import not_none

# TODO complete signatures
# TODO consider moving to zig
# TODO handle constrained attribute

# TODO strategy with traits:
# just make everything an instance trait,
# and later when we performance optimize reconsider

if TYPE_CHECKING:
    import faebryk.library._F as F


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


OperandPointer = Collections.AbstractPointer(
    edge_factory=lambda identifier: fbrk.EdgeOperand.build(
        operand_identifier=identifier
    ),
    retrieval_function=lambda node: _retrieve_operands(node, None)[0],
)

OperandSequence = Collections.AbstractSequence(
    edge_factory=lambda identifier, order: fbrk.EdgeOperand.build(
        operand_identifier=identifier
    ),
    retrieval_function=_retrieve_operands,
)

OperandSet = Collections.AbstractSet(
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

    def get_operands(self) -> list["F.Parameters.can_be_operand"]:
        node = fabll.Traits(self).get_obj_raw()
        operands: list[Parameters.can_be_operand] = []
        pointers = node.get_children(
            direct_only=True,
            types=(OperandPointer, OperandSequence, OperandSet),  # type: ignore
        )
        for pointer in pointers:
            child = cast(F.Collections.PointerProtocol, pointer)
            li = child.as_list()
            assert all(c.isinstance(Parameters.can_be_operand) for c in li)
            li = cast(list[Parameters.can_be_operand], li)
            operands.extend(li)

        return operands

    def get_operand_operatables(self) -> set["F.Parameters.is_parameter_operatable"]:
        return self.get_operands_with_trait(Parameters.is_parameter_operatable)

    def get_operands_with_trait[T: fabll.NodeT](
        self, trait: type[T], recursive: bool = False
    ) -> set[T]:
        return (
            {
                t
                for op in self.get_operands()
                if (t := fabll.Traits(op).try_get_trait_of_obj(trait))
            }
            | {
                inner
                for t_e in self.get_operands_with_trait(is_expression)
                for inner in t_e.get_operands_with_trait(trait, recursive=recursive)
            }
            if recursive
            else set()
        )

    def get_operand_literals(self) -> dict[int, "F.Literals.is_literal"]:
        return {
            i: t
            for i, op in enumerate(self.get_operands())
            if (t := fabll.Traits(op).try_get_trait_of_obj(Literals.is_literal))
        }

    def get_operand_leaves_operatable(
        self,
    ) -> set["F.Parameters.is_parameter_operatable"]:
        # TODO
        raise NotImplementedError

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
        self, context: "Parameters.ReprContext | None" = None, use_name: bool = False
    ) -> str:
        # TODO
        raise NotImplementedError()

    def as_parameter_operatable(self) -> "F.Parameters.is_parameter_operatable":
        return fabll.Traits(self).get_trait_of_obj(Parameters.is_parameter_operatable)

    def as_operand(self) -> "F.Parameters.can_be_operand":
        return fabll.Traits(self).get_trait_of_obj(Parameters.can_be_operand)

    def is_congruent_to_factory(
        self,
        other_factory: "type[fabll.NodeT]",
        other_operands: Sequence["F.Parameters.can_be_operand"],
        allow_uncorrelated: bool = False,
        # TODO
        check_constrained: bool = True,
    ) -> bool:
        # TODO
        pass

    @staticmethod
    def sort_by_depth[T: fabll.NodeT](exprs: Iterable[T], ascending: bool) -> list[T]:
        """
        Ascending:
        ```
        (A + B) + (C + D)
        -> [A, B, C, D, (A+B), (C+D), (A+B)+(C+D)]
        ```
        """
        # TODO
        pass

    def get_obj_type_node(self) -> graph.BoundNode:
        return not_none(fabll.Traits(self).get_obj_raw().get_type_node())

    def get_uncorrelatable_literals(self) -> list[Literals.is_literal]:
        # TODO
        raise NotImplementedError

    def expr_isinstance(self, *expr_types: type[fabll.NodeT]) -> bool:
        return fabll.Traits(self).get_obj_raw().isinstance(*expr_types)

    def expr_try_cast[T: fabll.NodeT](self, t: type[T]) -> T | None:
        return fabll.Traits(self).get_obj_raw().try_cast(t)

    def expr_cast[T: fabll.NodeT](self, t: type[T], check: bool = True) -> T:
        return fabll.Traits(self).get_obj_raw().cast(t, check=check)

    def is_congruent_to(
        self,
        other: "fabll.NodeT",
        recursive: bool = False,
        allow_uncorrelated: bool = False,
        check_constrained: bool = True,
    ) -> bool:
        # TODO
        raise NotImplementedError

    def in_operands(self, operand: "F.Parameters.can_be_operand") -> bool:
        return operand in self.get_operands()

    @staticmethod
    def are_pos_congruent(
        left: Sequence["F.Parameters.can_be_operand"],
        right: Sequence["F.Parameters.can_be_operand"],
        commutative: bool = False,
        allow_uncorrelated: bool = False,
        check_constrained: bool = True,
    ) -> bool:
        # TODO
        raise NotImplementedError


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


def _make_instance_from_operand_instance[T: fabll.NodeT](
    expr_factory: type[T],
    operand_instances: "tuple[F.Parameters.can_be_operand, ...]",
    g: graph.GraphView | None,
) -> T:
    if not operand_instances:
        raise ValueError("At least one operand is required")
    g = g or operand_instances[0].instance.g()
    tg = operand_instances[0].tg
    return expr_factory.bind_typegraph(tg=tg).create_instance(g=g)


def _op(expr: fabll.NodeT) -> "F.Parameters.can_be_operand":
    from faebryk.library.Parameters import can_be_operand

    return expr.get_trait(can_be_operand)


# --------------------------------------------------------------------------------------

# TODO distribute
# TODO implement functions


class is_arithmetic(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    # _unit = F.Units.HasUnit.MakeChild()


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

    def as_parameter_operatable(
        self,
    ) -> "F.Parameters.is_parameter_operatable":
        return fabll.Traits(self).get_trait_of_obj(Parameters.is_parameter_operatable)


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
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g))


class Subtract(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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

    @classmethod
    def from_operands(
        cls,
        minuend: "F.Parameters.can_be_operand",
        *subtrahends: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        operands = (minuend, *subtrahends)
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(minuend, *subtrahends)

    @classmethod
    def c(
        cls,
        minuend: "F.Parameters.can_be_operand",
        *subtrahends: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(minuend, *subtrahends, g=g))


class Multiply(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g))


class Divide(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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

    @classmethod
    def from_operands(
        cls,
        numerator: "F.Parameters.can_be_operand",
        *denominators: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        operands = (numerator, *denominators)
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(numerator, *denominators)

    @classmethod
    def c(
        cls,
        numerator: "F.Parameters.can_be_operand",
        *denominators: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(numerator, *denominators, g=g))


class Sqrt(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g))


class Power(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        base: "F.Parameters.can_be_operand",
        exponent: "F.Parameters.can_be_operand",
    ) -> Self:
        self.base.get().point(base)
        self.exponent.get().point(exponent)
        return self

    @classmethod
    def from_operands(
        cls,
        base: "F.Parameters.can_be_operand",
        exponent: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (base, exponent), g=g)
        return instance.setup(base, exponent)

    @classmethod
    def c(
        cls,
        base: "F.Parameters.can_be_operand",
        exponent: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(base, exponent, g=g))


class Log(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        operand: "F.Parameters.can_be_operand",
        base: "F.Parameters.can_be_operand | None" = None,
    ) -> Self:
        self.operand.get().point(operand)
        if base is not None:
            self.base.get().point(base)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        base: "F.Parameters.can_be_operand | None" = None,
        g: graph.GraphView | None = None,
    ) -> Self:
        operands = (operand, base) if base is not None else (operand,)
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(operand, base)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        base: "F.Parameters.can_be_operand | None" = None,
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, base, g=g))


class Sin(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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

    def setup(self, operand: "F.Parameters.can_be_operand") -> Self:
        self.operand.get().point(operand)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g))


class Cos(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="cos",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    operand = OperandPointer.MakeChild()

    def setup(self, operand: "F.Parameters.can_be_operand") -> Self:
        self.operand.get().point(operand)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g))


class Abs(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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

    def setup(self, operand: "F.Parameters.can_be_operand") -> Self:
        self.operand.get().point(operand)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g))


class Round(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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

    def setup(self, operand: "F.Parameters.can_be_operand") -> Self:
        self.operand.get().point(operand)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g))


class Floor(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="⌊",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: "F.Parameters.can_be_operand") -> Self:
        self.operand.get().point(operand)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g))


class Ceil(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    _is_expression = is_expression.MakeChild(
        repr_style=is_expression.ReprStyle(
            symbol="⌈",
            placement=is_expression.ReprStyle.Placement.PREFIX,
        )
    )

    operand = OperandPointer.MakeChild()

    def setup(self, operand: "F.Parameters.can_be_operand") -> Self:
        self.operand.get().point(operand)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g))


class Min(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="min",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: "F.Parameters.can_be_operand") -> Self:
        self.operands.get().append(*operands)
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g))


class Max(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    _is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="max",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: "F.Parameters.can_be_operand") -> Self:
        self.operands.get().append(*operands)
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g))


class Integrate(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        operand: "F.Parameters.can_be_operand",
        variable: "F.Parameters.can_be_operand",
    ) -> Self:
        self.function.get().point(operand)
        self.variable.get().point(variable)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        variable: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand, variable), g=g)
        return instance.setup(operand, variable)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        variable: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, variable, g=g))


class Differentiate(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        operand: "F.Parameters.can_be_operand",
        variable: "F.Parameters.can_be_operand",
    ) -> Self:
        self.function.get().point(operand)
        self.variable.get().point(variable)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        variable: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand, variable), g=g)
        return instance.setup(operand, variable)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        variable: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, variable, g=g))


class And(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        self,
        *operands: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(*operands, constrain=constrain)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, constrain=constrain))


class Or(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        self,
        *operands: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(*operands, constrain=constrain)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, constrain=constrain))


class Not(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        self, operand: "F.Parameters.can_be_operand", constrain: bool = True
    ) -> Self:
        self.operand.get().point(operand)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g)
        return instance.setup(operand, constrain=constrain)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g, constrain=constrain))


class Xor(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        self,
        *operands: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(*operands, constrain=constrain)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, constrain=constrain))


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
        antecedent: "F.Parameters.can_be_operand",
        consequent: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.antecedent.get().point(antecedent)
        self.consequent.get().point(consequent)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        antecedent: "F.Parameters.can_be_operand",
        consequent: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (antecedent, consequent), g=g
        )
        return instance.setup(antecedent, consequent, constrain=constrain)

    @classmethod
    def c(
        cls,
        antecedent: "F.Parameters.can_be_operand",
        consequent: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(antecedent, consequent, g=g, constrain=constrain))


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
        condition: "F.Parameters.can_be_operand",
        then_value: "F.Parameters.can_be_operand",
        else_value: "F.Parameters.can_be_operand",
    ) -> Self:
        self.condition.get().point(condition)
        self.then_value.get().point(then_value)
        self.else_value.get().point(else_value)
        return self

    @classmethod
    def from_operands(
        cls,
        condition: "F.Parameters.can_be_operand",
        then_value: "F.Parameters.can_be_operand",
        else_value: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (condition, then_value, else_value), g=g
        )
        return instance.setup(condition, then_value, else_value)

    @classmethod
    def c(
        cls,
        condition: "F.Parameters.can_be_operand",
        then_value: "F.Parameters.can_be_operand",
        else_value: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(condition, then_value, else_value, g=g))


class Union(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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

    def setup(self, *operands: "F.Parameters.can_be_operand") -> Self:
        self.operands.get().append(*operands)
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g))


class Intersection(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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

    def setup(self, *operands: "F.Parameters.can_be_operand") -> Self:
        self.operands.get().append(*operands)
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g))


class Difference(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        minuend: "F.Parameters.can_be_operand",
        subtrahend: "F.Parameters.can_be_operand",
    ) -> Self:
        self.minuend.get().point(minuend)
        self.subtrahend.get().point(subtrahend)
        return self

    @classmethod
    def from_operands(
        cls,
        minuend: "F.Parameters.can_be_operand",
        subtrahend: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (minuend, subtrahend), g=g)
        return instance.setup(minuend, subtrahend)

    @classmethod
    def c(
        cls,
        minuend: "F.Parameters.can_be_operand",
        subtrahend: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(minuend, subtrahend, g=g))


class SymmetricDifference(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        return self

    @classmethod
    def from_operands(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g)
        return instance.setup(left, right)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g))


class LessThan(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g)
        return instance.setup(left, right, constrain=constrain)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g, constrain=constrain))


class GreaterThan(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g)
        return instance.setup(left, right, constrain=constrain)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g, constrain=constrain))


class LessOrEqual(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g)
        return instance.setup(left, right, constrain=constrain)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g, constrain=constrain))


class GreaterOrEqual(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g)
        return instance.setup(left, right, constrain=constrain)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g, constrain=constrain))


class NotEqual(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g)
        return instance.setup(left, right, constrain=constrain)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g, constrain=constrain))


class IsBitSet(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        value: "F.Parameters.can_be_operand",
        bit_index: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.value.get().point(value)
        self.bit_index.get().point(bit_index)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        value: "F.Parameters.can_be_operand",
        bit_index: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (value, bit_index), g=g)
        return instance.setup(value, bit_index, constrain=constrain)

    @classmethod
    def c(
        cls,
        value: "F.Parameters.can_be_operand",
        bit_index: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(value, bit_index, g=g, constrain=constrain))


class IsSubset(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        subset: "F.Parameters.can_be_operand",
        superset: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.subset.get().point(subset)
        self.superset.get().point(superset)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        subset: "F.Parameters.can_be_operand",
        superset: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (subset, superset), g=g)
        return instance.setup(subset, superset, constrain=constrain)

    @classmethod
    def c(
        cls,
        subset: "F.Parameters.can_be_operand",
        superset: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(subset, superset, g=g, constrain=constrain))


class IsSuperset(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        superset: "F.Parameters.can_be_operand",
        subset: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.superset.get().point(superset)
        self.subset.get().point(subset)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        superset: "F.Parameters.can_be_operand",
        subset: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (superset, subset), g=g)
        return instance.setup(superset, subset, constrain=constrain)

    @classmethod
    def c(
        cls,
        superset: "F.Parameters.can_be_operand",
        subset: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(superset, subset, g=g, constrain=constrain))


class Cardinality(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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
        set: "F.Parameters.can_be_operand",
        cardinality: "F.Parameters.can_be_operand",
        constrain: bool = True,
    ) -> Self:
        self.set.get().point(set)
        self.cardinality.get().point(cardinality)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def from_operands(
        cls,
        set: "F.Parameters.can_be_operand",
        cardinality: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (set, cardinality), g=g)
        return instance.setup(set, cardinality, constrain=constrain)

    @classmethod
    def c(
        cls,
        set: "F.Parameters.can_be_operand",
        cardinality: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(set, cardinality, g=g, constrain=constrain))


class Is(fabll.Node):
    _can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
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

    def setup(
        self,
        operands: list["F.Parameters.can_be_operand"],
        constrain: bool = True,
    ) -> Self:
        self.operands.get().append(*operands)
        if constrain:
            self._is_constrainable.get().constrain()
        return self

    @classmethod
    def MakeChild_Constrain(
        cls, operands: list[fabll.RefPath]
    ) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            fabll.Traits.MakeEdge(IsConstrained.MakeChild(), [out]),
            identifier="constrain",
        )
        for operand in operands:
            # TODO: relying on a string identifier to connect to the correct
            # trait is nasty
            operand.append("_can_be_operand")
            out.add_dependant(
                OperandSet.MakeEdge([out, cls.operands], operand),
                identifier="connect_operands",
            )
        return out

    def get_other_operand(
        self, operand: "F.Parameters.can_be_operand"
    ) -> "F.Parameters.can_be_operand":
        return next(
            op for op in self.get_trait(is_expression).get_operands() if op != operand
        )

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g)
        return instance.setup(
            operands=list(operands),
            constrain=constrain,
        )

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        constrain: bool = True,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, constrain=constrain))
