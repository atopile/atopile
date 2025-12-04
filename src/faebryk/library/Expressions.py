from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Iterable, Self, Sequence

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
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
    typename="OperandPointer",
)

OperandSequence = Collections.AbstractSequence(
    edge_factory=lambda identifier, order: fbrk.EdgeOperand.build(
        operand_identifier=identifier
    ),
    retrieval_function=_retrieve_operands,
    typename="OperandSequence",
)

OperandSet = Collections.AbstractSet(
    edge_factory=lambda identifier, order: fbrk.EdgeOperand.build(
        operand_identifier=identifier
    ),
    retrieval_function=_retrieve_operands,
    typename="OperandSet",
)


class is_expression(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    repr_placement = F.Collections.Pointer.MakeChild()
    repr_symbol = F.Collections.Pointer.MakeChild()

    as_parameter_operatable = fabll.Traits.ImpliedTrait(
        Parameters.is_parameter_operatable
    )
    as_operand = fabll.Traits.ImpliedTrait(Parameters.can_be_operand)

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

    _repr_enum = F.Literals.EnumsFactory(ReprStyle.Placement)

    @classmethod
    def MakeChild(cls, repr_style: ReprStyle) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        cls._MakeReprStyle(out, repr_style)
        return out

    @classmethod
    def _MakeReprStyle(cls, out: fabll._ChildField[Self], repr_style: ReprStyle):
        Collections.Pointer.MakeEdgeForField(
            out,
            [out, cls.repr_placement],
            cls._repr_enum.MakeChild(repr_style.placement),
        )
        Collections.Pointer.MakeEdgeForField(
            out,
            [out, cls.repr_symbol],
            Literals.Strings.MakeChild(repr_style.symbol or "<NONE>"),
        )

    def get_repr_style(self) -> ReprStyle:
        placement = not_none(
            self.repr_placement.get()
            .deref()
            .cast(type(self)._repr_enum)
            .get_single_value_typed(is_expression.ReprStyle.Placement)
        )
        symbol = not_none(
            self.repr_symbol.get().deref().cast(F.Literals.Strings)
        ).get_values()[0]
        if symbol == "<NONE>":
            symbol = None
        return is_expression.ReprStyle(placement=placement, symbol=symbol)

    def get_operands(self) -> list["F.Parameters.can_be_operand"]:
        from faebryk.library.Collections import PointerProtocol

        node = fabll.Traits(self).get_obj_raw()
        operands: list[Parameters.can_be_operand] = []
        pointers: set[PointerProtocol] = (
            node.get_children(
                direct_only=True,
                types=OperandPointer,  # type: ignore
            )
            | node.get_children(
                direct_only=True,
                types=OperandSequence,  # type: ignore
            )
            | node.get_children(
                direct_only=True,
                types=OperandSet,  # type: ignore
            )
        )
        for pointer in pointers:
            li = pointer.as_list()
            li_op = [c.cast(Parameters.can_be_operand) for c in li]
            operands.extend(li_op)

        return operands

    def get_operand_operatables(self) -> set["F.Parameters.is_parameter_operatable"]:
        return self.get_operands_with_trait(Parameters.is_parameter_operatable)

    def get_operands_with_trait[T: fabll.NodeT](
        self, trait: type[T], recursive: bool = False
    ) -> set[T]:
        return {
            t for op in self.get_operands() if (t := op.try_get_sibling_trait(trait))
        } | (
            {
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
            if (t := op.try_get_sibling_trait(Literals.is_literal))
        }

    def get_operand_leaves_operatable(
        self,
    ) -> set["F.Parameters.is_parameter_operatable"]:
        """
        Recursively get all leaf operatables (parameters that are not expressions).
        For expressions, descends into their operands until reaching parameters.

        Example:
        ```
        (A + B) * C -> {A, B, C}
        ```
        """
        result: set[Parameters.is_parameter_operatable] = set()
        for operand in self.get_operands():
            if expr := operand.try_get_sibling_trait(is_expression):
                # Operand is an expression - recurse into it
                result.update(expr.get_operand_leaves_operatable())
            elif operand_po := operand.try_get_sibling_trait(
                Parameters.is_parameter_operatable
            ):
                # Operand is a leaf (parameter or literal with is_parameter_operatable)
                result.add(operand_po)
        return result

    def compact_repr(
        self, context: "Parameters.ReprContext | None" = None, use_name: bool = False
    ) -> str:
        if context is None:
            context = Parameters.ReprContext()

        style = self.get_repr_style()
        symbol = style.symbol
        if symbol is None:
            symbol = type(self).__name__

        symbol_suffix = ""
        if self.try_get_sibling_trait(is_predicate):
            # symbol = f"\033[4m{symbol}!\033[0m"
            symbol_suffix += "!"
            from faebryk.core.solver.mutator import is_terminated

            if self.try_get_sibling_trait(is_terminated):
                symbol_suffix += "!"
        symbol += symbol_suffix
        lit_suffix = self.as_parameter_operatable.get()._get_lit_suffix()
        symbol += lit_suffix

        def format_operand(op: Parameters.can_be_operand):
            if lit := op.try_get_sibling_trait(Literals.is_literal):
                return lit.pretty_str()
            if po := op.get_sibling_trait(F.Parameters.is_parameter_operatable):
                op_out = po.compact_repr(context, use_name=use_name)
                if (op_expr := op.try_get_sibling_trait(is_expression)) and len(
                    op_expr.get_operands()
                ) > 1:
                    op_out = f"({op_out})"
                return op_out
            return str(op)

        formatted_operands = [format_operand(op) for op in self.get_operands()]
        out = ""
        if style.placement == is_expression.ReprStyle.Placement.PREFIX:
            if len(formatted_operands) == 1:
                out = f"{symbol}{formatted_operands[0]}"
            else:
                out = f"{symbol}({', '.join(formatted_operands)})"
        elif style.placement == is_expression.ReprStyle.Placement.EMBRACE:
            out = f"{symbol}{', '.join(formatted_operands)}{style.symbol}"
        elif len(formatted_operands) == 0:
            out = f"{type(self).__name__}{symbol_suffix}()"
        elif style.placement == is_expression.ReprStyle.Placement.POSTFIX:
            if len(formatted_operands) == 1:
                out = f"{formatted_operands[0]}{symbol}"
            else:
                out = f"({', '.join(formatted_operands)}){symbol}"
        elif len(formatted_operands) == 1:
            out = f"{type(self).__name__}{symbol_suffix}({formatted_operands[0]})"
        elif lit_suffix and len(formatted_operands) > 2:
            out = (
                f"{type(self).__name__}{symbol_suffix}{lit_suffix}"
                f"({', '.join(formatted_operands)})"
            )
        elif style.placement == is_expression.ReprStyle.Placement.INFIX:
            symbol = f" {symbol} "
            out = f"{symbol.join(formatted_operands)}"
        elif style.placement == is_expression.ReprStyle.Placement.INFIX_FIRST:
            if len(formatted_operands) == 2:
                out = f"{formatted_operands[0]} {symbol} {formatted_operands[1]}"
            else:
                out = (
                    f"{formatted_operands[0]}{symbol}("
                    f"{', '.join(formatted_operands[1:])})"
                )
        else:
            assert False
        assert out

        # out += self._get_lit_suffix()

        return out

    def is_congruent_to_factory(
        self,
        other_factory: "type[fabll.NodeT]",
        other_operands: Sequence["F.Parameters.can_be_operand"],
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        allow_uncorrelated: bool = False,
        check_constrained: bool = True,
    ) -> bool:
        """
        Check if this expression is congruent to an expression that would be
        created from the given factory with the given operands.

        This is useful for checking if creating a new expression would be
        redundant because an equivalent one already exists.

        Args:
            other_factory: The expression type (e.g., Add, Multiply)
            other_operands: The operands that would be used
            allow_uncorrelated: If True, non-singleton literals can match
            check_constrained: If True, also check constrained literals

        Returns:
            True if this expression is congruent to what the factory would create
        """
        # Get the underlying expression node
        self_obj = fabll.Traits(self).get_obj_raw()

        # Check if this expression is an instance of the factory type
        if not self_obj.isinstance(other_factory):
            return False

        # Check if the factory type is commutative
        type_node = self_obj.bind_typegraph_from_instance(self_obj.instance)
        commutative = (
            is_commutative.is_commutative_type(type_node) if type_node else False
        )

        # Check operand congruence
        out = is_expression.are_pos_congruent(
            self.get_operands(),
            list(other_operands),
            commutative=commutative,
            g=g,
            tg=tg,
            allow_uncorrelated=allow_uncorrelated,
            check_constrained=check_constrained,
        )
        return out

    @staticmethod
    def sort_by_depth[T: fabll.NodeT](exprs: Iterable[T], ascending: bool) -> list[T]:
        """
        Ascending:
        ```
        (A + B) + (C + D)
        -> [A, B, C, D, (A+B), (C+D), (A+B)+(C+D)]
        ```
        """
        return sorted(
            exprs,
            key=lambda e: e.get_trait(Parameters.is_parameter_operatable).get_depth(),
            reverse=not ascending,
        )

    @staticmethod
    def sort_by_depth_po(
        exprs: Iterable["F.Parameters.is_parameter_operatable"],
        ascending: bool,
    ) -> list["F.Parameters.is_parameter_operatable"]:
        return sorted(
            exprs,
            key=Parameters.is_parameter_operatable.get_depth,
            reverse=not ascending,
        )

    def get_obj_type_node(self) -> graph.BoundNode:
        return not_none(fabll.Traits(self).get_obj_raw().get_type_node())

    def get_uncorrelatable_literals(self) -> list[Literals.is_literal]:
        """
        Get all literals in this expression's operands that cannot be correlated.

        Uncorrelatable literals are those that are neither singleton nor empty,
        meaning they represent a range or set of values that cannot be uniquely
        identified for congruence matching.

        Returns:
            List of uncorrelatable literal traits from this expression's operands
        """
        return [
            lit
            for lit in self.get_operand_literals().values()
            if lit.is_not_correlatable()
        ]

    def expr_isinstance(self, *expr_types: type[fabll.NodeT]) -> bool:
        return fabll.Traits(self).get_obj_raw().isinstance(*expr_types)

    def expr_try_cast[T: fabll.NodeT](self, t: type[T]) -> T | None:
        return fabll.Traits(self).get_obj_raw().try_cast(t)

    def expr_cast[T: fabll.NodeT](self, t: type[T], check: bool = True) -> T:
        return fabll.Traits(self).get_obj_raw().cast(t, check=check)

    def get_sorted_operands(self) -> list["F.Parameters.can_be_operand"]:
        return is_expression._sorted_operands(self.get_operands())

    @staticmethod
    def _sorted_operands(
        operands: Sequence["F.Parameters.can_be_operand"],
    ) -> list["F.Parameters.can_be_operand"]:
        # TODO not sure this still works the same way as back in the day
        return sorted(operands, key=hash)

    def is_congruent_to(
        self,
        other: "is_expression",
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        recursive: bool = False,
        allow_uncorrelated: bool = False,
        check_constrained: bool = True,
    ) -> bool:
        """
        Check if this expression is congruent to another expression.

        Two expressions are congruent if:
        - They are the same type
        - They have congruent operands (same nodes or equal correlatable literals)

        Args:
            other: The other expression (or its is_expression trait)
            recursive: If True, recursively check sub-expression congruence
            allow_uncorrelated: If True, non-singleton literals can match
            check_constrained: If True, also check constrained literals

        Returns:
            True if the expressions are congruent
        """
        if self.is_same(other):
            return True

        # TODO handle non-operands

        self_obj = fabll.Traits(self).get_obj_raw()
        other_obj = fabll.Traits(other).get_obj_raw()

        # Must be same type
        if not self_obj.has_same_type_as(other_obj):
            return False

        # if lit is non-single/empty set we can't correlate thus can't be congruent
        #  in general
        if not allow_uncorrelated and (
            self.get_uncorrelatable_literals() or other.get_uncorrelatable_literals()
        ):
            return False

        if check_constrained and (
            self_obj.has_trait(is_predicate) != other_obj.has_trait(is_predicate)
        ):
            return False

        # Check if the expression is commutative
        commutative = is_commutative.is_commutative_type(
            not_none(self_obj.bind_typegraph_from_instance(self_obj.instance))
        )
        self_operands = self.get_operands()
        other_operands = other.get_operands()

        if self_operands == other_operands:
            return True
        if commutative and self.get_sorted_operands() == other.get_sorted_operands():
            return True

        # Check operand congruence
        return recursive and is_expression.are_pos_congruent(
            self_operands,
            other_operands,
            g=g,
            tg=tg,
            commutative=commutative,
            allow_uncorrelated=allow_uncorrelated,
            check_constrained=check_constrained,
        )

    def in_operands(self, operand: "F.Parameters.can_be_operand") -> bool:
        return operand in self.get_operands()

    @staticmethod
    def are_pos_congruent(
        left: Sequence["F.Parameters.can_be_operand"],
        right: Sequence["F.Parameters.can_be_operand"],
        g: graph.GraphView,
        tg: fbrk.TypeGraph,
        commutative: bool = False,
        allow_uncorrelated: bool = False,
        check_constrained: bool = True,
    ) -> bool:
        """
        Check if two sequences of operands are positionally congruent.

        Two operands are congruent if:
        - They are the same node (by reference)
        - They are both correlatable literals with equal values

        Args:
            left: First operand sequence
            right: Second operand sequence
            commutative: If True, order doesn't matter (for commutative operations)
            allow_uncorrelated: If True, non-singleton/non-empty literals can match
            check_constrained: If True, also check constrained literals

        Returns:
            True if the operand sequences are congruent
        """
        if commutative:
            left = is_expression._sorted_operands(left)
            right = is_expression._sorted_operands(right)

        if len(left) != len(right):
            return False

        def operands_congruent(
            op1: Parameters.can_be_operand,
            op2: Parameters.can_be_operand,
        ) -> bool:
            # Same node - congruent
            if op1.is_same(op2):
                return True

            op1_obj = fabll.Traits(op1).get_obj_raw()
            op2_obj = fabll.Traits(op2).get_obj_raw()
            if not op1_obj.has_same_type_as(op2_obj):
                return False

            if lit1 := op1_obj.try_get_trait(Literals.is_literal):
                lit2 = op2_obj.get_trait(Literals.is_literal)
                if not allow_uncorrelated and (
                    lit1.is_not_correlatable() or lit2.is_not_correlatable()
                ):
                    return False
                return bool(lit1.equals(lit2, g=g, tg=tg))

            if expr1 := op1_obj.try_get_trait(is_expression):
                expr2 = op2_obj.get_trait(is_expression)
                return expr1.is_congruent_to(
                    expr2,
                    g=g,
                    tg=tg,
                    recursive=True,
                    allow_uncorrelated=allow_uncorrelated,
                    check_constrained=check_constrained,
                )

            # params only congruent if same node i guess?

            return False

        return all(
            operands_congruent(le, ri) for le, ri in zip(left, right, strict=True)
        )

    def get_depth(self) -> int:
        """
        Returns depth of longest expression tree from this expression.
        ```
        ((A + B) + (C + D)) * 5
            ^    ^    ^     ^
            0    1    0     2

        a = (X + (Y + Z))
        (a + 1) + a
         ^ ^    ^ ^
         1 2    3 1
        ```
        """
        return 1 + max(
            [op.get_depth() for op in self.get_operands_with_trait(is_expression)] + [0]
        )


# TODO
class has_implicit_constraints(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_assertable(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    as_expression = fabll.Traits.ImpliedTrait(is_expression)
    as_parameter_operatable = fabll.Traits.ImpliedTrait(
        Parameters.is_parameter_operatable
    )
    as_operand = fabll.Traits.ImpliedTrait(Parameters.can_be_operand)

    # TODO: solver_terminated flag, has to be attr

    def assert_(self):
        parent = self.get_parent_force()[0]
        return fabll.Traits.create_and_add_instance_to(node=parent, trait=is_predicate)


class is_predicate(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def unassert(self):
        # TODO
        pass


def _make_instance_from_operand_instance[T: fabll.NodeT](
    expr_factory: type[T],
    operand_instances: "tuple[F.Parameters.can_be_operand, ...]",
    g: graph.GraphView | None,
    tg: fbrk.TypeGraph | None,
) -> T:
    if not operand_instances and (not g or not tg):
        raise ValueError("At least one operand is required if no graph is provided")
    g = g or operand_instances[0].instance.g()
    tg = tg or operand_instances[0].tg
    return expr_factory.bind_typegraph(tg=tg).create_instance(g=g)


def _op(expr: fabll.NodeT) -> "F.Parameters.can_be_operand":
    from faebryk.library.Parameters import can_be_operand

    return expr.get_trait(can_be_operand)


# --------------------------------------------------------------------------------------

# TODO distribute
# TODO implement functions


class is_arithmetic(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_additive(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_functional(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_logic(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_setic(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_numeric_predicate(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_setic_predicate(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class has_side_effects(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


# solver specific


class is_canonical(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    as_expression = fabll.Traits.ImpliedTrait(is_expression)
    as_parameter_operatable = fabll.Traits.ImpliedTrait(
        Parameters.is_parameter_operatable
    )
    as_operand = fabll.Traits.ImpliedTrait(F.Parameters.can_be_operand)


class is_reflexive(fabll.Node):
    """
    f(x,x) == true
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_idempotent(fabll.Node):
    """
    f^n(x) == f(x) | n>0
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class has_idempotent_operands(fabll.Node):
    """
    f(x,x) == x
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_commutative(fabll.Node):
    """
    f(x,y) == f(y,x)
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    @classmethod
    def is_commutative_type(cls, node_type: fabll.TypeNodeBoundTG[Any, Any]) -> bool:
        return node_type.check_if_instance_of_type_has_trait(is_commutative)


class has_unary_identity(fabll.Node):
    """
    f(x,𝜖) == x
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_associative(fabll.Node):
    """
    f(f(x,y),z) == f(x,f(y,z))
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_flattenable(fabll.Node):
    """
    f(f(x,y),z) == f(x,y,z)
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_involutory(fabll.Node):
    """
    f(f(x)) == x
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


# TODO expression class that captures not(f(x,y)) == f(y, x)

# --------------------------------------------------------------------------------------


class Add(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="+",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())
    has_unary_identity = fabll.Traits.MakeEdge(has_unary_identity.MakeChild())
    is_fully_associative = fabll.Traits.MakeEdge(is_associative.MakeChild())
    is_associative = fabll.Traits.MakeEdge(is_flattenable.MakeChild())

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: "Parameters.can_be_operand") -> Self:
        self.operands.get().append(*operands)
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, tg=tg))


class Subtract(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        operands = (minuend, *subtrahends)
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(minuend, *subtrahends)

    @classmethod
    def c(
        cls,
        minuend: "F.Parameters.can_be_operand",
        *subtrahends: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(minuend, *subtrahends, g=g, tg=tg))


class Multiply(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="*",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())
    has_unary_identity = fabll.Traits.MakeEdge(has_unary_identity.MakeChild())
    is_fully_associative = fabll.Traits.MakeEdge(is_associative.MakeChild())
    is_associative = fabll.Traits.MakeEdge(is_flattenable.MakeChild())

    operands = OperandSet.MakeChild()

    @classmethod
    def MakeChild_FromOperands(
        cls, *operand_fields: fabll._ChildField
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)

        for operand_field in operand_fields:
            # TODO: to can_be_operand?
            out.add_dependant(OperandSet.MakeEdge([out, cls.operands], [operand_field]))

        return out

    def setup(self, *operands: "Parameters.can_be_operand") -> Self:
        self.operands.get().append(*operands)
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, tg=tg))


class Divide(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="/",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    # denominator not zero
    has_implicit_constraints = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        operands = (numerator, *denominators)
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(numerator, *denominators)

    @classmethod
    def c(
        cls,
        numerator: "F.Parameters.can_be_operand",
        *denominators: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(numerator, *denominators, g=g, tg=tg))


class Sqrt(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="√",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    # non-negative
    has_implicit_constraints = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g, tg=tg)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g, tg=tg))


class Power(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="^",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())

    base = OperandPointer.MakeChild()
    exponent = OperandPointer.MakeChild()

    @classmethod
    def MakeChild_FromOperands(
        cls, base: fabll._ChildField, exponent: fabll._ChildField
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(OperandPointer.MakeEdge([out, cls.base], [base]))
        out.add_dependant(OperandPointer.MakeEdge([out, cls.exponent], [exponent]))
        return out

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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (base, exponent), g=g, tg=tg
        )
        return instance.setup(base, exponent)

    @classmethod
    def c(
        cls,
        base: "F.Parameters.can_be_operand",
        exponent: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(base, exponent, g=g, tg=tg))


class Log(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="log",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())

    # non-negative
    has_implicit_constraints = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        operands = (operand, base) if base is not None else (operand,)
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(operand, base)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        base: "F.Parameters.can_be_operand | None" = None,
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, base, g=g, tg=tg))


class Sin(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="sin",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())

    operand = OperandPointer.MakeChild()

    def setup(self, operand: "F.Parameters.can_be_operand") -> Self:
        self.operand.get().point(operand)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g, tg=tg)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g, tg=tg))


class Cos(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g, tg=tg)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g, tg=tg))


class Abs(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="|",
                placement=is_expression.ReprStyle.Placement.EMBRACE,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    is_idempotent = fabll.Traits.MakeEdge(is_idempotent.MakeChild())

    operand = OperandPointer.MakeChild()

    def setup(self, operand: "F.Parameters.can_be_operand") -> Self:
        self.operand.get().point(operand)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g, tg=tg)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g, tg=tg))


class Round(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="round",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    is_idempotent = fabll.Traits.MakeEdge(is_idempotent.MakeChild())

    operand = OperandPointer.MakeChild()

    def setup(self, operand: "F.Parameters.can_be_operand") -> Self:
        self.operand.get().point(operand)
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g, tg=tg)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g, tg=tg))


class Floor(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g, tg=tg)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g, tg=tg))


class Ceil(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = is_expression.MakeChild(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g, tg=tg)
        return instance.setup(operand)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g, tg=tg))


class Min(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, tg=tg))


class Max(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, tg=tg))


class Integrate(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (operand, variable), g=g, tg=tg
        )
        return instance.setup(operand, variable)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        variable: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, variable, g=g, tg=tg))


class Differentiate(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (operand, variable), g=g, tg=tg
        )
        return instance.setup(operand, variable)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        variable: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, variable, g=g, tg=tg))


class And(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
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
        assert_: bool = False,
    ) -> Self:
        self.operands.get().append(*operands)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(*operands, assert_=assert_)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, tg=tg, assert_=assert_))


class Or(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="∨",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    has_idempotent_operands = fabll.Traits.MakeEdge(has_idempotent_operands.MakeChild())
    is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())
    has_unary_identity = fabll.Traits.MakeEdge(has_unary_identity.MakeChild())
    is_fully_associative = fabll.Traits.MakeEdge(is_associative.MakeChild())
    is_associative = fabll.Traits.MakeEdge(is_flattenable.MakeChild())

    operands = OperandSequence.MakeChild()

    def setup(
        self,
        *operands: "F.Parameters.can_be_operand",
        assert_: bool = False,
    ) -> Self:
        self.operands.get().append(*operands)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(*operands, assert_=assert_)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, tg=tg, assert_=assert_))


class Not(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="¬",
                placement=is_expression.ReprStyle.Placement.PREFIX,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    is_involutory = fabll.Traits.MakeEdge(is_involutory.MakeChild())

    operand = OperandPointer.MakeChild()

    def setup(
        self, operand: "F.Parameters.can_be_operand", assert_: bool = False
    ) -> Self:
        self.operand.get().point(operand)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (operand,), g=g, tg=tg)
        return instance.setup(operand, assert_=assert_)

    @classmethod
    def c(
        cls,
        operand: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(operand, g=g, tg=tg, assert_=assert_))


class Xor(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
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
        assert_: bool = False,
    ) -> Self:
        self.operands.get().append(*operands)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(*operands, assert_=assert_)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, tg=tg, assert_=assert_))


class Implies(fabll.Node):
    as_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
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
        assert_: bool = False,
    ) -> Self:
        self.antecedent.get().point(antecedent)
        self.consequent.get().point(consequent)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        antecedent: "F.Parameters.can_be_operand",
        consequent: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (antecedent, consequent), g=g, tg=tg
        )
        return instance.setup(antecedent, consequent, assert_=assert_)

    @classmethod
    def c(
        cls,
        antecedent: "F.Parameters.can_be_operand",
        consequent: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(
            cls.from_operands(antecedent, consequent, g=g, tg=tg, assert_=assert_)
        )


class IfThenElse(fabll.Node):
    has_side_effects = fabll.Traits.MakeEdge(has_side_effects.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (condition, then_value, else_value), g=g, tg=tg
        )
        return instance.setup(condition, then_value, else_value)

    @classmethod
    def c(
        cls,
        condition: "F.Parameters.can_be_operand",
        then_value: "F.Parameters.can_be_operand",
        else_value: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(condition, then_value, else_value, g=g, tg=tg))

    def try_run(self):
        # TODO
        pass


class Union(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="∪",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    has_idempotent_operands = fabll.Traits.MakeEdge(has_idempotent_operands.MakeChild())
    is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())
    has_unary_identity = fabll.Traits.MakeEdge(has_unary_identity.MakeChild())
    is_fully_associative = fabll.Traits.MakeEdge(is_associative.MakeChild())
    is_associative = fabll.Traits.MakeEdge(is_flattenable.MakeChild())

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: "F.Parameters.can_be_operand") -> Self:
        self.operands.get().append(*operands)
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, tg=tg))


class Intersection(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="∩",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    has_idempotent_operands = fabll.Traits.MakeEdge(has_idempotent_operands.MakeChild())
    is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())
    has_unary_identity = fabll.Traits.MakeEdge(has_unary_identity.MakeChild())
    is_fully_associative = fabll.Traits.MakeEdge(is_associative.MakeChild())
    is_associative = fabll.Traits.MakeEdge(is_flattenable.MakeChild())

    operands = OperandSequence.MakeChild()

    def setup(self, *operands: "F.Parameters.can_be_operand") -> Self:
        self.operands.get().append(*operands)
        return self

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(*operands)

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, tg=tg))


class Difference(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (minuend, subtrahend), g=g, tg=tg
        )
        return instance.setup(minuend, subtrahend)

    @classmethod
    def c(
        cls,
        minuend: "F.Parameters.can_be_operand",
        subtrahend: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(minuend, subtrahend, g=g, tg=tg))


class SymmetricDifference(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="△",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())

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
        tg: fbrk.TypeGraph | None = None,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g, tg=tg)
        return instance.setup(left, right)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g, tg=tg))


class LessThan(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
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
        assert_: bool = False,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g, tg=tg)
        return instance.setup(left, right, assert_=assert_)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g, tg=tg, assert_=assert_))


class GreaterThan(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol=">",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        assert_: bool = False,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g, tg=tg)
        return instance.setup(left, right, assert_=assert_)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g, tg=tg, assert_=assert_))


class LessOrEqual(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
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
        assert_: bool = False,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g, tg=tg)
        return instance.setup(left, right, assert_=assert_)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g, tg=tg, assert_=assert_))


class GreaterOrEqual(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="≥",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    is_reflexive = fabll.Traits.MakeEdge(is_reflexive.MakeChild())

    left = OperandPointer.MakeChild()
    right = OperandPointer.MakeChild()

    def setup(
        self,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        assert_: bool = False,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g, tg=tg)
        return instance.setup(left, right, assert_=assert_)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g, tg=tg, assert_=assert_))


class NotEqual(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
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
        assert_: bool = False,
    ) -> Self:
        self.left.get().point(left)
        self.right.get().point(right)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, (left, right), g=g, tg=tg)
        return instance.setup(left, right, assert_=assert_)

    @classmethod
    def c(
        cls,
        left: "F.Parameters.can_be_operand",
        right: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(left, right, g=g, tg=tg, assert_=assert_))


class IsBitSet(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="b[]",
                placement=is_expression.ReprStyle.Placement.INFIX,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())

    value = OperandPointer.MakeChild()
    bit_index = OperandPointer.MakeChild()

    def setup(
        self,
        value: "F.Parameters.can_be_operand",
        bit_index: "F.Parameters.can_be_operand",
        assert_: bool = False,
    ) -> Self:
        self.value.get().point(value)
        self.bit_index.get().point(bit_index)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        value: "F.Parameters.can_be_operand",
        bit_index: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (value, bit_index), g=g, tg=tg
        )
        return instance.setup(value, bit_index, assert_=assert_)

    @classmethod
    def c(
        cls,
        value: "F.Parameters.can_be_operand",
        bit_index: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(value, bit_index, g=g, tg=tg, assert_=assert_))


class IsSubset(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="⊆",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    is_reflexive = fabll.Traits.MakeEdge(is_reflexive.MakeChild())

    subset = OperandPointer.MakeChild()
    superset = OperandPointer.MakeChild()

    def setup(
        self,
        subset: "F.Parameters.can_be_operand",
        superset: "F.Parameters.can_be_operand",
        assert_: bool = False,
    ) -> Self:
        self.subset.get().point(subset)
        self.superset.get().point(superset)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        subset: "F.Parameters.can_be_operand",
        superset: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (subset, superset), g=g, tg=tg
        )
        return instance.setup(subset, superset, assert_=assert_)

    @classmethod
    def c(
        cls,
        subset: "F.Parameters.can_be_operand",
        superset: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(subset, superset, g=g, tg=tg, assert_=assert_))


class IsSuperset(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
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
        assert_: bool = False,
    ) -> Self:
        self.superset.get().point(superset)
        self.subset.get().point(subset)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        superset: "F.Parameters.can_be_operand",
        subset: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (superset, subset), g=g, tg=tg
        )
        return instance.setup(superset, subset, assert_=assert_)

    @classmethod
    def c(
        cls,
        superset: "F.Parameters.can_be_operand",
        subset: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(superset, subset, g=g, tg=tg, assert_=assert_))


class Cardinality(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
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
        assert_: bool = False,
    ) -> Self:
        self.set.get().point(set)
        self.cardinality.get().point(cardinality)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def from_operands(
        cls,
        set: "F.Parameters.can_be_operand",
        cardinality: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(
            cls, (set, cardinality), g=g, tg=tg
        )
        return instance.setup(set, cardinality, assert_=assert_)

    @classmethod
    def c(
        cls,
        set: "F.Parameters.can_be_operand",
        cardinality: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(set, cardinality, g=g, tg=tg, assert_=assert_))


class Is(fabll.Node):
    can_be_operand = fabll.Traits.MakeEdge(F.Parameters.can_be_operand.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(
        Parameters.is_parameter_operatable.MakeChild()
    )
    is_reflexive = fabll.Traits.MakeEdge(is_reflexive.MakeChild())
    is_assertable = fabll.Traits.MakeEdge(is_assertable.MakeChild())
    is_expression = fabll.Traits.MakeEdge(
        is_expression.MakeChild(
            repr_style=is_expression.ReprStyle(
                symbol="is",
                placement=is_expression.ReprStyle.Placement.INFIX_FIRST,
            )
        )
    )
    is_canonical = fabll.Traits.MakeEdge(is_canonical.MakeChild())
    is_commutative = fabll.Traits.MakeEdge(is_commutative.MakeChild())

    operands = OperandSet.MakeChild()

    def setup(
        self,
        *operands: "F.Parameters.can_be_operand",
        assert_: bool = False,
    ) -> Self:
        self.operands.get().append(*operands)
        if assert_:
            self.is_assertable.get().assert_()
        return self

    @classmethod
    def MakeChild_Constrain(
        cls, operands: list[fabll.RefPath]
    ) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            fabll.Traits.MakeEdge(is_predicate.MakeChild(), [out]),
            identifier="constrain",
        )
        for operand in operands:
            # TODO: relying on a string identifier to connect to the correct
            # trait is nasty
            operand.append("can_be_operand")
            out.add_dependant(
                OperandSet.MakeEdge([out, cls.operands], operand),
                identifier="connect_operands",
            )
        return out

    def get_other_operand(
        self, operand: "F.Parameters.can_be_operand"
    ) -> "F.Parameters.can_be_operand | None":
        return next(
            (
                op
                for op in self.is_expression.get().get_operands()
                if not op.is_same(operand)
            ),
            None,
        )

    @classmethod
    def from_operands(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> Self:
        instance = _make_instance_from_operand_instance(cls, operands, g=g, tg=tg)
        return instance.setup(
            *operands,
            assert_=assert_,
        )

    @classmethod
    def c(
        cls,
        *operands: "F.Parameters.can_be_operand",
        g: graph.GraphView | None = None,
        tg: fbrk.TypeGraph | None = None,
        assert_: bool = False,
    ) -> "F.Parameters.can_be_operand":
        return _op(cls.from_operands(*operands, g=g, tg=tg, assert_=assert_))


# Tests --------------------------------------------------------------------------------


def test_repr_style():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    or_ = Or.bind_typegraph(tg=tg).create_instance(g=g)

    or_repr = or_.is_expression.get().get_repr_style()
    assert or_repr.placement == is_expression.ReprStyle.Placement.INFIX
    assert or_repr.symbol == "∨"


def test_compact_repr():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    p1 = Parameters.BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    p2 = Parameters.BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    or_ = Or.c(
        p1.can_be_operand.get(),
        p2.can_be_operand.get(),
        assert_=True,
    )
    or_repr = or_.get_sibling_trait(is_expression).compact_repr()
    assert or_repr == "A ∨! B"


if __name__ == "__main__":
    import typer

    typer.run(test_compact_repr)
