# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum, auto
from itertools import chain
from types import NotImplementedType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Self,
    Sequence,
    TypeGuard,
    cast,
    override,
)

from faebryk.core.core import Namespace
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.node import Node, f_field
from faebryk.core.trait import Trait
from faebryk.libs.sets.numeric_sets import NumberLike
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
    Quantity_Set,
    Quantity_Set_Discrete,
    QuantityLikeR,
)
from faebryk.libs.sets.sets import BoolSet, EnumSet, P_Set, as_lit
from faebryk.libs.units import (
    HasUnit,
    Quantity,
    Unit,
    UnitCompatibilityError,
    assert_compatible_units,
    dimensionless,
    quantity,
)
from faebryk.libs.util import (
    KeyErrorAmbiguous,
    KeyErrorNotFound,
    SyncedFlag,
    abstract,
    cast_assert,
    find,
    once,
    unique,
)

if TYPE_CHECKING:
    from faebryk.core.solver.solver import Solver

logger = logging.getLogger(__name__)


class ParameterOperableException(Exception):
    def __init__(self, parameter: "ParameterOperatable", msg: str):
        self.parameter = parameter
        super().__init__(msg)


class ParameterOperableHasNoLiteral(ParameterOperableException):
    pass


# When we make this generic, two types, type T of elements, and type S of known subsets
# boolean: T == S == bool
# enum: T == S == Enum
# number: T == Number type, S == Range[Number]
class ParameterOperatable(Node):
    type QuantityLike = Quantity | Unit | NotImplementedType
    type Number = int | float | QuantityLike

    type NumberLiteral = Number | P_Set[Number] | Quantity_Set
    type NumberLike = ParameterOperatable | NumberLiteral
    type BooleanLiteral = bool | BoolSet
    type BooleanLike = ParameterOperatable | BooleanLiteral
    type EnumLiteral = Enum | EnumSet
    type EnumLike = ParameterOperatable | EnumLiteral
    type SetLiteral = NumberLiteral | BooleanLiteral | EnumLiteral

    type All = NumberLike | BooleanLike | EnumLike
    type Literal = NumberLiteral | BooleanLiteral | EnumLiteral | SetLiteral
    type Sets = All

    operated_on: GraphInterface

    constrained: bool = False
    """
    Shortcut for `isinstance(self, ConstrainableExpression) and self.constrained`
    """

    @property
    def domain(self) -> "Domain": ...

    def has_implicit_constraint(self) -> bool: ...

    def has_implicit_constraints_recursive(self) -> bool: ...

    def operation_add(self, other: NumberLike):
        return Add(self, other)

    def operation_subtract(self: NumberLike, other: NumberLike):
        return Subtract(self, other)

    def operation_multiply(self, other: NumberLike):
        return Multiply(self, other)

    def operation_divide(self: NumberLike, other: NumberLike):
        return Divide(self, other)

    def operation_power(self, other: NumberLike):
        return Power(base=self, exponent=other)

    def operation_log(self):
        return Log(self)

    def operation_sqrt(self):
        return Sqrt(self)

    def operation_abs(self):
        return Abs(self)

    def operation_min(self):
        return Min(self)

    def operation_max(self):
        return Max(self)

    def operation_integrate(self, variable: "Parameter"):
        return Integrate(self, variable)

    def operation_differentiate(self, variable: "Parameter"):
        return Differentiate(self, variable)

    def operation_negate(self):
        return Multiply(self, quantity(-1))

    def operation_invert(self):
        return Power(self, -1)

    def operation_floor(self):
        return Floor(self)

    def operation_ceil(self):
        return Ceil(self)

    def operation_round(self):
        return Round(self)

    def operation_sin(self):
        return Sin(self)

    def operation_cos(self):
        return Cos(self)

    def operation_union(self, other: Sets):
        return Union(self, other)

    def operation_intersection(self, other: Sets):
        return Intersection(self, other)

    def operation_difference(self, *subtrahends: Sets):
        return Difference(minuend=self, *subtrahends)

    def operation_symmetric_difference(self, other: Sets):
        return SymmetricDifference(self, other)

    def operation_and(self, other: BooleanLike):
        return And(self, other)

    def operation_or(self, other: BooleanLike):
        return Or(self, other)

    def operation_not(self):
        return Not(self)

    def operation_xor(self, other: BooleanLike):
        return Xor(self, other)

    def operation_implies(self, other: BooleanLike):
        return Implies(condition=self, implication=other)

    def operation_is_le(self, other: NumberLike):
        return LessOrEqual(left=self, right=other)

    def operation_is_ge(self, other: NumberLike):
        return GreaterOrEqual(left=self, right=other)

    def operation_is_lt(self, other: NumberLike):
        return LessThan(left=self, right=other)

    def operation_is_gt(self, other: NumberLike):
        return GreaterThan(left=self, right=other)

    def operation_is_ne(self, other: NumberLike):
        return NotEqual(left=self, right=other)

    def operation_is_bit_set(self, index: NumberLike):
        return IsBitSet(self, index=index)

    def operation_is_subset(self, other: Sets):
        return IsSubset(left=self, right=other)

    def operation_is_superset(self, other: Sets):
        return IsSuperset(left=self, right=other)

    # Run by the solver on finalization
    inspect_solution: Callable[[Self], None] = lambda _: None

    def inspect_add_on_solution(self, fun: Callable[[Self], None]) -> None:
        current = self.inspect_solution

        def new(self2):
            current(self2)
            fun(self2)

        self.inspect_solution = new

    # ----------------------------------------------------------------------------------
    # Generic
    def alias_is(self, other: All):
        return Is(self, other).constrain()

    # Numberlike
    def constrain_le(self, other: NumberLike):
        return self.operation_is_le(other).constrain()

    def constrain_ge(self, other: NumberLike):
        return self.operation_is_ge(other).constrain()

    def constrain_lt(self, other: NumberLike):
        # makes implementation easier for now
        # le should be enough
        raise NotImplementedError()
        return self.operation_is_lt(other).constrain()

    def constrain_gt(self, other: NumberLike):
        # makes implementation easier for now
        # ge should be enough
        raise NotImplementedError()
        return self.operation_is_gt(other).constrain()

    def constrain_ne(self, other: NumberLike):
        # want to see when this is useful in practice
        raise NotImplementedError()
        return self.operation_is_ne(other).constrain()

    # Setlike
    def constrain_subset(self, other: Sets):
        return self.operation_is_subset(other).constrain()

    def constrain_superset(self, other: Sets):
        return self.operation_is_superset(other).constrain()

    def constrain_cardinality(self, other: int):
        return Cardinality(self, other).constrain()

    # ----------------------------------------------------------------------------------
    def __add__(self, other: NumberLike):
        return self.operation_add(other)

    def __radd__(self, other: NumberLike):
        return self.operation_add(other)

    def __sub__(self, other: NumberLike):
        # TODO could be set difference
        return self.operation_subtract(other)

    def __rsub__(self, other: NumberLike):
        return type(self).operation_subtract(other, self)

    def __mul__(self, other: NumberLike):
        return self.operation_multiply(other)

    def __rmul__(self, other: NumberLike):
        return self.operation_multiply(other)

    def __truediv__(self, other: NumberLike):
        return self.operation_divide(other)

    def __rtruediv__(self, other: NumberLike):
        return type(self).operation_divide(other, self)

    def __pow__(self, other: NumberLike):
        return self.operation_power(other)

    def __abs__(self):
        return self.operation_abs()

    def __neg__(self):
        return self.operation_negate()

    def __round__(self):
        return self.operation_round()

    def __floor__(self):
        return self.operation_floor()

    def __ceil__(self):
        return self.operation_ceil()

    def __le__(self, other: NumberLike):
        return self.operation_is_le(other)

    def __ge__(self, other: NumberLike):
        return self.operation_is_ge(other)

    def __lt__(self, other: NumberLike):
        return self.operation_is_lt(other)

    def __gt__(self, other: NumberLike):
        return self.operation_is_gt(other)

    def __ne__(self, other: NumberLike):
        return self.operation_is_ne(other)

    # bitwise and
    def __and__(self, other: BooleanLike):
        # TODO could be set intersection
        return self.operation_and(other)

    def __rand__(self, other: BooleanLike):
        return self.operation_and(other)

    def __or__(self, other: BooleanLike):
        # TODO could be set union
        return self.operation_or(other)

    def __ror__(self, other: BooleanLike):
        return self.operation_or(other)

    def __xor__(self, other: BooleanLike):
        return self.operation_xor(other)

    def __rxor__(self, other: BooleanLike):
        return self.operation_xor(other)

    # ----------------------------------------------------------------------------------

    def operation_switch_case_subset(
        self,
        cases: Iterable[tuple[Literal, "ConstrainableExpression"]],
    ) -> "ConstrainableExpression":
        exprs = [(IsSubset(self, lit), case) for lit, case in cases]
        return ConstrainableExpression.operation_switch_case_implications(exprs)

    def operation_mapping(
        self,
        other: "ParameterOperatable",
        mapping: dict[Literal, Literal],
    ) -> "ConstrainableExpression":
        exprs = [
            (lit_self, IsSubset(other, lit_other))
            for lit_self, lit_other in mapping.items()
        ]
        return self.operation_switch_case_subset(exprs)

    def constrain_mapping(
        self, other: "ParameterOperatable", mapping: dict[Literal, Literal]
    ):
        return self.operation_mapping(other, mapping).constrain()

    # ----------------------------------------------------------------------------------
    def get_operations[T: "Expression"](
        self,
        types: type[T] | None = None,
        constrained_only: bool = False,
        recursive: bool = False,
    ) -> set[T]:
        if types is None:
            types = Expression  # type: ignore
        types = cast(type[T], types)
        assert issubclass(types, Expression)

        out = cast(set[T], self.operated_on.get_connected_nodes(types=[types]))
        if recursive:
            for o in list(out):
                out.update(o.get_operations(recursive=True))
        if constrained_only:
            assert issubclass(types, ConstrainableExpression)
            out = {i for i in out if cast(ConstrainableExpression, i).constrained}
        return out

    def get_literal(self, op: type["ConstrainableExpression"] | None = None) -> Literal:
        """
        ```
        P(self, X) ∧ P.constrained -> return X
        ```
        """
        if op is None:
            op = Is
        # we have logic for is and is_subset in this function,
        # let's find a usecase for other ops before allowing them
        if not issubclass(op, (Is, IsSubset)):
            raise ValueError(f"Unsupported op {op}")
        ops = self.get_operations(op, constrained_only=True)
        try:
            if op is IsSubset:
                literals = find(
                    lit
                    for op in ops
                    for (i, lit) in op.get_operand_literals().items()
                    if i > 0
                )
            else:
                literals = find(
                    lit for op in ops for (_, lit) in op.get_operand_literals().items()
                )
        except KeyErrorNotFound as e:
            raise ParameterOperableHasNoLiteral(
                self, f"Parameter {self} has no literal for op {op}"
            ) from e
        except KeyErrorAmbiguous as e:
            duplicates = e.duplicates
            if issubclass(op, Is):
                if len(unique(duplicates, key=lambda x: as_lit(x))) != 1:
                    raise
                return duplicates[0]
            elif issubclass(op, IsSubset):
                return P_Set.intersect_all(*duplicates)
            else:
                raise
        return literals

    def try_get_literal_subset(self) -> Literal | None:
        lits = self.try_get_literal_for_multiple_ops([Is, IsSubset])
        if not lits:
            return None
        if len(lits) == 1:
            return next(iter(lits.values()))

        is_lit, ss_lit = map(P_Set.from_value, (lits[Is], lits[IsSubset]))
        if not is_lit.is_subset_of(ss_lit):
            raise KeyErrorAmbiguous(list(lits.values()))
        return is_lit

    def try_get_literal(
        self, op: type["ConstrainableExpression"] | None = None
    ) -> Literal | None:
        try:
            return self.get_literal(op)
        except ParameterOperableHasNoLiteral:
            return None

    def try_get_literal_for_multiple_ops(
        self, ops: list[type["ConstrainableExpression"]]
    ) -> dict[type["ConstrainableExpression"], Literal] | None:
        lits = {op: self.try_get_literal(op) for op in ops}
        lits = {op: lit for op, lit in lits.items() if lit is not None}
        return lits if lits else None

    @staticmethod
    def try_extract_literal(
        po: "ParameterOperatable.All", allow_subset: bool = False
    ) -> Literal | None:
        if ParameterOperatable.is_literal(po):
            return po
        assert isinstance(po, ParameterOperatable)
        if allow_subset:
            return po.try_get_literal_subset()
        return po.try_get_literal()

    # type checks

    # TODO Quantity_Interval_Disjoint is also a literal
    @staticmethod
    def is_number_literal(value: Any) -> TypeGuard[QuantityLike]:
        return isinstance(value, QuantityLikeR)

    @staticmethod
    def is_literal(value: Any) -> TypeGuard[Literal]:
        return not isinstance(value, ParameterOperatable)

    @dataclass
    class ReprContext:
        @dataclass
        class VariableMapping:
            mapping: dict["Parameter", int] = field(default_factory=dict)
            next_id: int = 0

        variable_mapping: VariableMapping = field(default_factory=VariableMapping)

        def __hash__(self) -> int:
            return hash(id(self))

    @once
    def compact_repr(
        self, context: ReprContext | None = None, use_name: bool = False
    ) -> str:
        raise NotImplementedError()

    # TODO move to Expression
    @staticmethod
    def sort_by_depth[T: ParameterOperatable](
        exprs: Iterable[T], ascending: bool
    ) -> list[T]:
        """
        Ascending:
        ```
        (A + B) + (C + D)
        -> [(A+B), (C+D), (A+B)+(C+D)]
        ```
        """
        return sorted(exprs, key=ParameterOperatable.get_depth, reverse=not ascending)

    @staticmethod
    def get_depth(po: "ParameterOperatable.All") -> int:
        if isinstance(po, Expression):
            return po.depth()
        return 0

    @once
    def _get_lit_suffix(self) -> str:
        out = ""
        try:
            lit = self.try_get_literal()
        except KeyErrorAmbiguous as e:
            return f"{{AMBIGUOUS_I: {e.duplicates}}}"
        if lit is not None:
            out = f"{{I|{lit}}}"
        elif (lit := self.try_get_literal_subset()) is not None:
            out = f"{{S|{lit}}}"
        if lit == BoolSet(True):
            out = "✓"
        elif lit == BoolSet(False) and isinstance(lit, (BoolSet, bool)):
            out = "✗"
        return out


def has_implicit_constraints_recursive(po: ParameterOperatable.All) -> bool:
    if isinstance(po, ParameterOperatable):
        return po.has_implicit_constraints_recursive()
    return False


@abstract
class Expression(ParameterOperatable):
    operates_on: GraphInterface

    def __init__(self, domain, *operands: ParameterOperatable.All):
        super().__init__()
        assert not any(o is None for o in operands)
        self._domain = domain
        self.operands = tuple(operands)
        self.operatable_operands: set[ParameterOperatable] = {
            op for op in operands if isinstance(op, ParameterOperatable)
        }
        self.non_operands = None

    def __preinit__(self):
        for op in self.operatable_operands:
            # TODO: careful here, we should make it more clear that operates_on just
            # expresses a relation but is not a replacement of self.operands
            if self.operates_on.is_connected_to(op.operated_on):
                continue
            self.operates_on.connect(op.operated_on)

    @staticmethod
    def is_uncorrelatable_literal(lit) -> bool:
        return not isinstance(lit, ParameterOperatable) and (
            not isinstance(lit, P_Set)
            or not (lit.is_single_element() or lit.is_empty())
        )

    @once
    def get_uncorrelatable_literals(self) -> list[ParameterOperatable.Literal]:
        # TODO we should just use the canonical lits, for now just no support
        # for non-canonical lits
        return [
            lit for lit in self.operands if Expression.is_uncorrelatable_literal(lit)
        ]

    @once
    def get_sorted_operands(self) -> list[ParameterOperatable]:
        return sorted(self.operands, key=hash)

    @once
    def is_congruent_to(
        self,
        other: "Expression",
        recursive: bool = False,
        allow_uncorrelated: bool = False,
        check_constrained: bool = True,
    ) -> bool:
        if self is other:
            return True
        if type(self) is not type(other):
            return False
        if len(self.operands) != len(other.operands):
            return False
        if self.non_operands or other.non_operands:
            return False
        # if lit is non-single/empty set we can't correlate thus can't be congruent
        #  in general
        if not allow_uncorrelated and (
            self.get_uncorrelatable_literals() or other.get_uncorrelatable_literals()
        ):
            return False
        if (
            check_constrained
            and isinstance(self, ConstrainableExpression)
            and self.constrained
            != cast_assert(ConstrainableExpression, other).constrained
        ):
            return False
        if self.operands == other.operands:
            return True
        if isinstance(self, Commutative):
            # fucking genius
            # lit hash is stable
            # paramop hash only same with same id
            left = self.get_sorted_operands()
            right = other.get_sorted_operands()
            if left == right:
                return True

        if recursive and Expression.are_pos_congruent(
            self.operands,
            other.operands,
            commutative=isinstance(self, Commutative),
            allow_uncorrelated=allow_uncorrelated,
            check_constrained=check_constrained,
        ):
            return True

        return False

    def is_congruent_to_factory(
        self,
        other_factory: type["Expression"],
        other_operands: Sequence[ParameterOperatable.All],
        allow_uncorrelated: bool = False,
        # TODO
        check_constrained: bool = True,
    ) -> bool:
        if type(self) is not other_factory:
            return False
        return Expression.are_pos_congruent(
            self.operands,
            other_operands,
            allow_uncorrelated=allow_uncorrelated,
            check_constrained=check_constrained,
        )

    @staticmethod
    def are_pos_congruent(
        left: Sequence[ParameterOperatable.All],
        right: Sequence[ParameterOperatable.All],
        commutative: bool = False,
        allow_uncorrelated: bool = False,
        check_constrained: bool = True,
    ) -> bool:
        if len(left) != len(right):
            return False

        if not allow_uncorrelated and any(
            Expression.is_uncorrelatable_literal(lit) for lit in chain(left, right)
        ):
            return False

        # FIXME handle commutative
        return all(
            lhs.is_congruent_to(
                rhs,
                recursive=True,
                allow_uncorrelated=allow_uncorrelated,
                check_constrained=check_constrained,
            )
            if isinstance(lhs, Expression) and isinstance(rhs, Expression)
            else lhs == rhs
            for lhs, rhs in zip(left, right)
        )

    @property
    def domain(self) -> "Domain":
        return self._domain

    def get_operand_operatables[T: ParameterOperatable](
        self, types: type[T] = ParameterOperatable, recursive: bool = False
    ) -> set[T]:
        out = set(self.operatable_operands)
        if recursive:
            for o in list(out):
                if not isinstance(o, Expression):
                    continue
                out.update(o.get_operand_operatables(recursive=True))
        if types is not ParameterOperatable:
            out = {o for o in out if isinstance(o, types)}
        return cast(set[T], out)

    def get_operand_expressions(self, recursive: bool = False) -> set["Expression"]:
        return self.get_operand_operatables(Expression, recursive=recursive)

    def get_operand_parameters(self, recursive: bool = False) -> set["Parameter"]:
        return self.get_operand_operatables(Parameter, recursive=recursive)

    def get_operand_literals(self) -> dict[int, ParameterOperatable.Literal]:
        return {
            i: o
            for i, o in enumerate(self.operands)
            if ParameterOperatable.is_literal(o)
        }

    def get_operand_leaves_operatable(self) -> set[ParameterOperatable]:
        ops = self.get_operand_operatables(recursive=True)
        return {
            o
            for o in ops
            if not isinstance(o, Expression)
            or not o.get_operand_operatables(recursive=False)
        }

    def depth(self) -> int:
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
        # FIXME this does not work (if expressions are added afterwards in the tree)
        if hasattr(self, "_depth"):
            return self._depth
        self._depth = 1 + max(
            [0] + [Expression.get_depth(op) for op in self.operands],
        )
        return self._depth

    def has_implicit_constraint(self) -> bool:
        return True  # opt out

    def has_implicit_constraints_recursive(self) -> bool:
        if self.has_implicit_constraint():
            return True
        for op in self.operands:
            if isinstance(op, Expression) and op.has_implicit_constraints_recursive():
                return True
        return False

    def get_other_operand(
        self, operand: ParameterOperatable.All
    ) -> ParameterOperatable.All:
        assert len(self.operands) == 2
        if self.operands[0] is operand:
            return self.operands[1]
        return self.operands[0]

    def __repr__(self) -> str:
        return f"{super().__repr__()}({self.operands})"

    @dataclass
    class ReprStyle:
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

    REPR_STYLE: ReprStyle = ReprStyle()

    def compact_repr(
        self,
        context: ParameterOperatable.ReprContext | None = None,
        use_name: bool = False,
    ) -> str:
        if context is None:
            context = ParameterOperatable.ReprContext()

        style = type(self).REPR_STYLE
        symbol = style.symbol
        if symbol is None:
            symbol = type(self).__name__

        symbol_suffix = ""
        if isinstance(self, ConstrainableExpression) and self.constrained:
            # symbol = f"\033[4m{symbol}!\033[0m"
            symbol_suffix += "!"
            if self._solver_terminated:
                symbol_suffix += "!"
        symbol += symbol_suffix
        lit_suffix = self._get_lit_suffix()
        symbol += lit_suffix

        def format_operand(op):
            if not isinstance(op, ParameterOperatable):
                return str(op)
            op_out = op.compact_repr(context, use_name=use_name)
            if isinstance(op, Expression) and len(op.operands) > 1:
                op_out = f"({op_out})"
            return op_out

        formatted_operands = [format_operand(op) for op in self.operands]
        out = ""
        if style.placement == Expression.ReprStyle.Placement.PREFIX:
            if len(formatted_operands) == 1:
                out = f"{symbol}{formatted_operands[0]}"
            else:
                out = f"{symbol}({', '.join(formatted_operands)})"
        elif style.placement == Expression.ReprStyle.Placement.EMBRACE:
            out = f"{symbol}{', '.join(formatted_operands)}{style.symbol}"
        elif len(formatted_operands) == 0:
            out = f"{type(self).__name__}{symbol_suffix}()"
        elif style.placement == Expression.ReprStyle.Placement.POSTFIX:
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
        elif style.placement == Expression.ReprStyle.Placement.INFIX:
            symbol = f" {symbol} "
            out = f"{symbol.join(formatted_operands)}"
        elif style.placement == Expression.ReprStyle.Placement.INFIX_FIRST:
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

    def __rich_repr__(self):
        if not self._is_setup:
            yield f"{type(self)}(not init)"
        else:
            yield self.compact_repr()


@abstract
class ConstrainableExpression(Expression):
    def __init__(self, *operands: ParameterOperatable.All):
        super().__init__(Boolean(), *operands)
        self.constrained: bool = False

        # TODO this should be done in solver, not here
        self._solver_terminated: bool = False
        """
        Flag marking to the solver that this predicate has been deduced to True.
        Differs from alias in the sense that we can guarantee that the predicate is
        True, while alias only marks that the predicate shall be True.
        """

    def _constrain(self, constraint: "Predicate"):
        constraint.constrain()

    # shortcuts
    def constrain(self):
        self.constrained = True
        return self

    # should be eager, in the sense that, if the outcome is known, the callable is
    # called immediately, without storing an expression
    # we must force a value (at the end of solving at the least)
    def if_then_else(
        self,
        if_true: Callable[[], Any] | None = None,
        if_false: Callable[[], Any] | None = None,
    ):
        return IfThenElse(self, if_true, if_false)

    @staticmethod
    def operation_switch_case_implications(
        cases: Iterable[tuple["ConstrainableExpression", "ConstrainableExpression"]],
    ) -> "ConstrainableExpression":
        return And(*(case.operation_implies(impl) for case, impl in cases))


@abstract
class Arithmetic(Expression):
    def __init__(self, *operands: ParameterOperatable.NumberLike):
        # HasUnit attr
        self.units: Unit = cast(Unit, None)  # checked in postinit

        super().__init__(Numbers(), *operands)
        types = (
            int,
            float,
            Quantity,
            Unit,
            Parameter,
            Arithmetic,
            Quantity_Interval,
            Quantity_Interval_Disjoint,
        )
        invalid_operands = [op for op in operands if not isinstance(op, types)]
        if invalid_operands:
            raise ValueError(
                "operands must be int, float, Quantity, Unit, Parameter, Arithmetic"
                ", Quantity_Interval, or Quantity_Interval_Disjoint"
                f", got {invalid_operands} with types"
                f" ([{', '.join(type(op).__name__ for op in invalid_operands)}])"
            )
        if any(
            not isinstance(param.domain, (Numbers, ESeries))
            for param in operands
            if isinstance(param, Parameter)
        ):
            raise ValueError("parameters must have domain Numbers or ESeries")

        # FIXME: convert to Quantity

        # TODO enforce
        self.operands = cast(tuple[ParameterOperatable.NumberLike, ...], operands)

    def __postinit__(self):
        assert self.units is not None


@abstract
class Additive(Arithmetic):
    def __init__(self, *operands):
        super().__init__(*operands)
        if not operands:
            self.units = dimensionless
        else:
            self.units = assert_compatible_units(operands)

    @staticmethod
    def sum(operands: Sequence[ParameterOperatable.NumberLike]) -> "Additive":
        # Else assert not correct
        if not len(operands):
            raise ValueError("at least one operand is required")
        return cast_assert(Additive, sum(operands))


class Add(Additive):
    REPR_STYLE = Additive.ReprStyle(
        symbol="+",
        placement=Additive.ReprStyle.Placement.INFIX,
    )

    def __init__(self, *operands):
        super().__init__(*operands)

    def has_implicit_constraint(self) -> bool:
        return False


class Subtract(Additive):
    REPR_STYLE = Additive.ReprStyle(
        symbol="-",
        placement=Additive.ReprStyle.Placement.INFIX,
    )

    def __init__(self, minuend, *subtrahend):
        super().__init__(minuend, *subtrahend)

    def has_implicit_constraint(self) -> bool:
        return False


class Multiply(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="*",
        placement=Arithmetic.ReprStyle.Placement.INFIX,
    )

    def __init__(self, *operands):
        super().__init__(*operands)
        units = [HasUnit.get_units_or_dimensionless(op) for op in operands]
        self.units = dimensionless
        for u in units:
            self.units = cast_assert(Unit, self.units * u)

    def has_implicit_constraint(self) -> bool:
        return False


class Divide(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="/",
        placement=Arithmetic.ReprStyle.Placement.INFIX,
    )

    def __init__(self, numerator, *denominator):
        super().__init__(numerator, *denominator)

        frac_unit = dimensionless
        for d in denominator:
            frac_unit = cast_assert(
                Unit, frac_unit * HasUnit.get_units_or_dimensionless(d)
            )

        self.units = cast_assert(
            Unit, HasUnit.get_units_or_dimensionless(numerator) / frac_unit
        )

    def has_implicit_constraint(self) -> bool:
        return True  # denominator not zero


class Sqrt(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="√",
        placement=Arithmetic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, operand):
        super().__init__(operand)
        self.units = operand.units**0.5

    def has_implicit_constraint(self) -> bool:
        return True  # non-negative


class Power(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="^",
        placement=Arithmetic.ReprStyle.Placement.INFIX_FIRST,
    )

    def __init__(self, base, exponent):
        super().__init__(base, exponent)

        exp_unit = HasUnit.get_units_or_dimensionless(exponent)
        if not exp_unit.is_compatible_with(dimensionless):
            raise UnitCompatibilityError(
                "exponent must have dimensionless unit",
                incompatible_items=[exponent],
            )
        base_unit = HasUnit.get_units_or_dimensionless(base)
        units = dimensionless
        if not base_unit.is_compatible_with(dimensionless):
            if isinstance(exponent, ParameterOperatable):
                raise NotImplementedError(
                    "exponent must be a literal for base with unit"
                )
            exp_val = Quantity_Interval_Disjoint.from_value(exponent)
            if exp_val.min_elem != exp_val.max_elem:
                raise ValueError(
                    "exponent must be a single value for non-dimensionless base"
                )
            units = base_unit**exp_val.min_elem.magnitude
        assert isinstance(units, Unit)
        self.units = units


class Log(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="log",
        placement=Arithmetic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, operand):
        super().__init__(operand)
        unit = HasUnit.get_units_or_dimensionless(operand)
        if not unit.is_compatible_with(dimensionless):
            raise ValueError("operand must have dimensionless unit")
        self.units = unit

        # TODO, be careful makes solver run forever like this
        # implicit constraint
        # if isinstance(operand, ParameterOperatable):
        #    operand.constrain_ge(lit(0))
        # elif Quantity_Interval_Disjoint.from_value(operand).min_elem < 0:
        #    raise ValueError("operand must be non-negative")

    def has_implicit_constraint(self) -> bool:
        return True  # non-negative


class Sin(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="sin",
        placement=Arithmetic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, operand):
        super().__init__(operand)
        unit = HasUnit.get_units_or_dimensionless(operand)
        if not unit.is_compatible_with(dimensionless):
            raise ValueError("operand must have dimensionless unit")
        self.units = unit

    def has_implicit_constraint(self) -> bool:
        return False


class Cos(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="cos",
        placement=Arithmetic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, operand):
        super().__init__(operand)
        unit = HasUnit.get_units_or_dimensionless(operand)
        if not unit.is_compatible_with(dimensionless):
            raise ValueError("operand must have dimensionless unit")
        self.units = unit

    def has_implicit_constraint(self) -> bool:
        return False


class Abs(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="|",
        placement=Arithmetic.ReprStyle.Placement.EMBRACE,
    )

    def __init__(self, operand):
        super().__init__(operand)
        self.units = HasUnit.get_units_or_dimensionless(operand)

    def has_implicit_constraint(self) -> bool:
        return False


class Round(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="round",
        placement=Arithmetic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, operand):
        super().__init__(operand)
        self.units = HasUnit.get_units_or_dimensionless(operand)

    def has_implicit_constraint(self) -> bool:
        return False


class Floor(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="⌊",
        placement=Arithmetic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, operand):
        super().__init__(operand)
        self.units = HasUnit.get_units_or_dimensionless(operand)

    def has_implicit_constraint(self) -> bool:
        return False


class Ceil(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="⌈",
        placement=Arithmetic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, operand):
        super().__init__(operand)
        self.units = HasUnit.get_units_or_dimensionless(operand)

    def has_implicit_constraint(self) -> bool:
        return False


class Min(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="min",
        placement=Arithmetic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, *operands):
        super().__init__(*operands)
        self.units = assert_compatible_units(operands)

    def has_implicit_constraint(self) -> bool:
        return False


class Max(Arithmetic):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="max",
        placement=Arithmetic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, *operands):
        super().__init__(*operands)
        self.units = assert_compatible_units(operands)

    def has_implicit_constraint(self) -> bool:
        return False


@abstract
class Functional(Arithmetic):
    def __init__(self, function: "ParameterOperatable", variable: "Parameter"):
        super().__init__(function, variable)


class Integrate(Functional):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="∫",
        placement=Arithmetic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, function: "ParameterOperatable", variable: "Parameter"):
        super().__init__(function, variable)
        # TODO units

    def has_implicit_constraint(self) -> bool:
        return False


class Differentiate(Functional):
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="d",
        placement=Arithmetic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, function: "ParameterOperatable", variable: "Parameter"):
        super().__init__(function, variable)
        # TODO units

    def has_implicit_constraint(self) -> bool:
        return False


class Logic(ConstrainableExpression):
    def __init__(self, *operands):
        super().__init__(*operands)
        types = bool, BoolSet, Parameter, Logic, Predicate
        if any(not isinstance(op, types) for op in operands):
            raise ValueError("operands must be bool, Parameter, Logic, or Predicate")
        if any(
            not isinstance(param.domain, Boolean)
            or not param.units.is_compatible_with(dimensionless)
            for param in operands
            if isinstance(param, Parameter)
        ):
            raise ValueError("parameters must have domain Boolean without a unit")


class And(Logic):
    REPR_STYLE = Logic.ReprStyle(
        symbol="∧",
        placement=Logic.ReprStyle.Placement.INFIX,
    )


class Or(Logic):
    REPR_STYLE = Logic.ReprStyle(
        symbol="∨",
        placement=Logic.ReprStyle.Placement.INFIX,
    )


class Not(Logic):
    REPR_STYLE = Logic.ReprStyle(
        symbol="¬",
        placement=Logic.ReprStyle.Placement.PREFIX,
    )

    def __init__(self, operand):
        super().__init__(operand)


class Xor(Logic):
    REPR_STYLE = Logic.ReprStyle(
        symbol="⊕",
        placement=Logic.ReprStyle.Placement.INFIX,
    )

    def __init__(self, *operands):
        super().__init__(*operands)


class Implies(Logic):
    REPR_STYLE = Logic.ReprStyle(
        symbol="⇒",
        placement=Logic.ReprStyle.Placement.INFIX_FIRST,
    )

    def __init__(self, condition, implication):
        super().__init__(condition, implication)


# TODO: consider making void return type expression
class IfThenElse(Expression):
    NON_OPERANDS_T = tuple[Callable[[], None], Callable[[], None], SyncedFlag]

    def __init__(
        self,
        condition: ParameterOperatable.BooleanLike,
        if_true: Callable[[], None] | None = None,
        if_false: Callable[[], None] | None = None,
        *,
        non_operands: NON_OPERANDS_T | None = None,
    ):
        # FIXME domain
        super().__init__(None, condition)

        # TODO a bit hacky
        if non_operands is None:
            non_operands = (
                if_true or (lambda: None),
                if_false or (lambda: None),
                SyncedFlag(),
            )
        self.non_operands = non_operands  # type: ignore

    def try_run(self):
        if self.fullfilled:
            return
        if isinstance(self.condition, ParameterOperatable):
            lit = self.condition.try_get_literal()
        else:
            lit = self.condition
        if lit is None or lit == BoolSet(True, False):
            return
        self.fullfilled = True

        if lit == BoolSet(True):
            self.if_true()
        else:
            assert lit == BoolSet(False)
            self.if_false()

    @property
    def condition(self) -> ConstrainableExpression | BoolSet:
        return cast_assert(ConstrainableExpression | BoolSet, self.operands[0])

    @property
    def _non_operands(self) -> NON_OPERANDS_T:
        return cast(IfThenElse.NON_OPERANDS_T, self.non_operands)

    @property
    def if_true(self) -> Callable[[], None]:
        return self._non_operands[0]

    @property
    def if_false(self) -> Callable[[], None]:
        return self._non_operands[1]

    @property
    def fullfilled(self) -> bool:
        return bool(self._non_operands[2])

    @fullfilled.setter
    def fullfilled(self, value: bool):
        self._non_operands[2].set(value)


class Setic(Expression):
    def __init__(self, *operands):
        # FIXME domain
        super().__init__(None, *operands)

        if len(operands) == 0:
            raise ValueError("Setic must have at least one operand")
        # types = (Parameter, ParameterOperatable.Sets)
        # if any(not isinstance(op, types) for op in operands):
        #    raise ValueError("operands must be Parameter or Set")
        units = [HasUnit.get_units_or_dimensionless(op) for op in operands]
        self.units = units[0]
        for u in units[1:]:
            if not self.units.is_compatible_with(u):
                raise ValueError("all operands must have compatible units")
        # TODO domain?


class Union(Setic):
    REPR_STYLE = Setic.ReprStyle(
        symbol="∪",
        placement=Setic.ReprStyle.Placement.INFIX,
    )


class Intersection(Setic):
    REPR_STYLE = Setic.ReprStyle(
        symbol="∩",
        placement=Setic.ReprStyle.Placement.INFIX,
    )


class Difference(Setic):
    REPR_STYLE = Setic.ReprStyle(
        symbol="−",
        placement=Setic.ReprStyle.Placement.INFIX,
    )

    def __init__(self, minuend, *subtrahends):
        super().__init__(minuend, *subtrahends)


class SymmetricDifference(Setic):
    REPR_STYLE = Setic.ReprStyle(
        symbol="△",
        placement=Setic.ReprStyle.Placement.INFIX,
    )

    def __init__(self, left, right):
        super().__init__(left, right)


class Domain:
    @staticmethod
    def get_shared_domain(*domains: "Domain") -> "Domain":
        if len(domains) == 0:
            raise ValueError("No domains provided")
        if len(domains) == 1:
            return domains[0]
        one = domains[0]
        two = domains[1]
        match one:
            case Boolean():
                if not isinstance(two, Boolean):
                    raise ValueError(
                        "Boolean domain cannot be mixed with other domains"
                    )
                shared = Boolean()
            case EnumDomain():
                if not isinstance(two, EnumDomain):
                    raise ValueError("Enum domain cannot be mixed with other domains")
                if one.enum_t != two.enum_t:
                    raise ValueError("Enum domains must be of the same type")
                shared = EnumDomain(one.enum_t)
            case Numbers():
                if not isinstance(two, Numbers):
                    raise ValueError(
                        "Numbers domain cannot be mixed with other domains"
                    )
                if (
                    isinstance(one, ESeries)
                    and isinstance(two, ESeries)
                    and one.series == two.series
                ):
                    shared = ESeries(one.series)
                else:
                    shared = Numbers(
                        negative=one.negative and two.negative,
                        zero_allowed=one.zero_allowed and two.zero_allowed,
                        integer=one.integer or two.integer,
                    )
            case _:
                raise ValueError("Unsupported domain")

        if len(domains) == 2:
            return shared
        return Domain.get_shared_domain(shared, *domains[2:])

    def unbounded(self, param: "Parameter") -> P_Set: ...

    def __repr__(self):
        # TODO make more informative
        return f"{type(self).__name__}()"


class Numbers(Domain):
    def __init__(
        self, *, negative: bool = True, zero_allowed: bool = True, integer: bool = False
    ) -> None:
        super().__init__()
        self.negative = negative
        self.zero_allowed = zero_allowed
        self.integer = integer

    @override
    def unbounded(self, param: "Parameter") -> Quantity_Interval_Disjoint:
        if self.integer:
            # TODO
            _max = int(1e15)
            _min = -_max if self.negative else 0
            return Quantity_Interval_Disjoint.from_value(
                Quantity_Interval(
                    min=quantity(_min, param.units),
                    max=quantity(_max, param.units),
                    units=param.units,
                )
            )
        if not self.zero_allowed:
            raise NotImplementedError("Non-zero unbounded not implemented")
        if not self.negative:
            return Quantity_Interval_Disjoint.from_value(
                Quantity_Interval(
                    min=quantity(0, param.units), max=None, units=param.units
                )
            )
        return Quantity_Interval_Disjoint.unbounded(param.units)


class ESeries(Numbers):
    class SeriesType(Enum):
        E6 = auto()
        E12 = auto()
        E24 = auto()
        E48 = auto()
        E96 = auto()
        E192 = auto()

    def __init__(self, series: SeriesType):
        super().__init__(negative=False, zero_allowed=False, integer=False)
        self.series = series


class Boolean(Domain):
    @override
    def unbounded(self, param: "Parameter") -> BoolSet:
        return BoolSet.unbounded()


class EnumDomain(Domain):
    def __init__(self, enum_t: type[Enum]):
        super().__init__()
        self.enum_t = enum_t

    @override
    def unbounded(self, param: "Parameter") -> EnumSet:
        return EnumSet.unbounded(self.enum_t)


class Predicate(ConstrainableExpression):
    def __init__(self, left, right):
        super().__init__(left, right)
        assert_compatible_units(self.operands)

    def __bool__(self):
        raise ValueError("Predicate cannot be converted to bool")


class NumericPredicate(Predicate):
    def __init__(self, left, right):
        super().__init__(left, right)

        for op in self.operands:
            if isinstance(op, Parameter) and not isinstance(
                op.domain, (Numbers, ESeries)
            ):
                raise ValueError(
                    "operand must have domain Numbers or ESeries,"
                    f" not {type(op.domain)}"
                )


class LessThan(NumericPredicate):
    REPR_STYLE = NumericPredicate.ReprStyle(
        symbol="<",
        placement=NumericPredicate.ReprStyle.Placement.INFIX_FIRST,
    )

    def __init__(self, left, right):
        # TODO we might allow it for integer domains at some point
        raise NotImplementedError(
            "'<' not supported, you very likely want to use '<=' instead"
        )
        super().__init__(left, right)


class GreaterThan(NumericPredicate):
    REPR_STYLE = NumericPredicate.ReprStyle(
        symbol=">",
        placement=NumericPredicate.ReprStyle.Placement.INFIX_FIRST,
    )


class LessOrEqual(NumericPredicate):
    REPR_STYLE = NumericPredicate.ReprStyle(
        symbol="≤",
        placement=NumericPredicate.ReprStyle.Placement.INFIX_FIRST,
    )


class GreaterOrEqual(NumericPredicate):
    REPR_STYLE = NumericPredicate.ReprStyle(
        symbol="≥",
        placement=NumericPredicate.ReprStyle.Placement.INFIX_FIRST,
    )


class NotEqual(NumericPredicate):
    REPR_STYLE = NumericPredicate.ReprStyle(
        symbol="≠",
        placement=NumericPredicate.ReprStyle.Placement.INFIX_FIRST,
    )


class IsBitSet(NumericPredicate):
    # TODO: consider making a BitwiseAnd that's more general
    REPR_STYLE = Arithmetic.ReprStyle(
        symbol="b[]",
        placement=Arithmetic.ReprStyle.Placement.INFIX,
    )

    def __init__(self, operand, index: NumberLike):
        super().__init__(operand, index)

        unit = HasUnit.get_units_or_dimensionless(operand)
        if not unit.is_compatible_with(dimensionless):
            raise ValueError("operand must have dimensionless unit")

        # check domain to be natural
        if isinstance(operand, ParameterOperatable):
            if not isinstance(operand.domain, Numbers) or not operand.domain.integer:
                raise ValueError("operand must have natural domain")
        else:
            # this is pretty ugly
            # TODO consider making a domain extraction function that handles any type
            if isinstance(operand, Quantity_Interval_Disjoint):
                if not operand.is_integer:
                    raise ValueError("operand must have integer domain")
            elif isinstance(operand, int):
                pass
            else:
                raise ValueError("operand must be a ParameterOperatable or int")

        _index = Quantity_Interval_Disjoint.from_value(index)
        if not _index.is_single_element() or not _index.is_integer or _index.any() < 0:
            raise ValueError("index must be a non-negative single integer")

    def has_implicit_constraint(self) -> bool:
        return False


class SeticPredicate(Predicate):
    def __init__(self, left, right):
        super().__init__(left, right)
        # types = ParameterOperatable, P_Set
        # TODO
        # if any(not isinstance(op, types) for op in self.operands):
        #    raise ValueError("operands must be Parameter or Set")
        units = [HasUnit.get_units_or_dimensionless(op) for op in self.operands]
        for u in units[1:]:
            if not units[0].is_compatible_with(u):
                raise ValueError("all operands must have compatible units")
        # TODO domain?


class IsSubset(SeticPredicate):
    REPR_STYLE = SeticPredicate.ReprStyle(
        symbol="⊆",
        placement=SeticPredicate.ReprStyle.Placement.INFIX_FIRST,
    )


class IsSuperset(SeticPredicate):
    REPR_STYLE = SeticPredicate.ReprStyle(
        symbol="⊇",
        placement=SeticPredicate.ReprStyle.Placement.INFIX_FIRST,
    )


class Cardinality(SeticPredicate):
    REPR_STYLE = SeticPredicate.ReprStyle(
        # TODO
        symbol="||",
        placement=SeticPredicate.ReprStyle.Placement.PREFIX,
    )

    def __init__(
        self, set: ParameterOperatable.Sets, cardinality: ParameterOperatable.NumberLike
    ):
        super().__init__(set, cardinality)


class Is(Predicate):
    REPR_STYLE = Predicate.ReprStyle(
        symbol="is",
        placement=Predicate.ReprStyle.Placement.INFIX_FIRST,
    )

    def __init__(self, left, right):
        super().__init__(left, right)


# TODO rename?
class R(Namespace):
    """
    Namespace holding Expressions, Domains and Predicates for Parameters.
    R = paRameters
    """

    class Predicates(Namespace):
        class Element(Namespace):
            LT = LessThan
            GT = GreaterThan
            LE = LessOrEqual
            GE = GreaterOrEqual
            NE = NotEqual

        class Set(Namespace):
            IS_SUBSET = IsSubset
            IS_SUPERSET = IsSuperset

    class Domains(Namespace):
        class ESeries(Namespace):
            E6 = lambda: ESeries(ESeries.SeriesType.E6)  # noqa: E731
            E12 = lambda: ESeries(ESeries.SeriesType.E12)  # noqa: E731
            E24 = lambda: ESeries(ESeries.SeriesType.E24)  # noqa: E731
            E48 = lambda: ESeries(ESeries.SeriesType.E48)  # noqa: E731
            E96 = lambda: ESeries(ESeries.SeriesType.E96)  # noqa: E731
            E192 = lambda: ESeries(ESeries.SeriesType.E192)  # noqa: E731

        class Numbers(Namespace):
            REAL = Numbers
            NATURAL = lambda: Numbers(integer=True, negative=False)  # noqa: E731

        BOOL = Boolean
        ENUM = EnumDomain

    class Expressions(Namespace):
        class Arithmetic(Namespace):
            ADD = Add
            SUBTRACT = Subtract
            MULTIPLY = Multiply
            DIVIDE = Divide
            POWER = Power
            LOG = Log
            SQRT = Sqrt
            LOG = Log
            ABS = Abs
            FLOOR = Floor
            CEIL = Ceil
            ROUND = Round
            SIN = Sin
            COS = Cos

        class Logic(Namespace):
            AND = And
            OR = Or
            NOT = Not
            XOR = Xor
            IMPLIES = Implies

        class Set(Namespace):
            UNION = Union
            INTERSECTION = Intersection
            DIFFERENCE = Difference
            SYMMETRIC_DIFFERENCE = SymmetricDifference


class Parameter(ParameterOperatable):
    class TraitT(Trait): ...

    def __init__(
        self,
        *,
        units: Unit | Quantity = dimensionless,
        # hard constraints
        within: Quantity_Interval_Disjoint | Quantity_Interval | None = None,
        domain: Domain = Numbers(negative=False),
        # soft constraints
        soft_set: Quantity_Interval_Disjoint | Quantity_Interval | None = None,
        guess: Quantity
        | int
        | float
        | None = None,  # TODO actually allowed to be anything from domain
        tolerance_guess: float | None = None,
        # hints
        likely_constrained: bool = False,  # TODO rename expect_constraits or similiar
    ):
        super().__init__()
        if within is not None and not within.units.is_compatible_with(units):
            raise ValueError("incompatible units")

        if isinstance(within, Quantity_Interval):
            within = Quantity_Interval_Disjoint(within)

        if isinstance(soft_set, Quantity_Interval):
            soft_set = Quantity_Interval_Disjoint(soft_set)

        if not isinstance(units, Unit):
            raise TypeError("units must be a Unit")
        self.units = units
        self.within = within
        self._domain = domain
        self.soft_set = soft_set
        self.guess = guess
        self.tolerance_guess = tolerance_guess
        self.likely_constrained = likely_constrained

    # Type forwards
    type All = ParameterOperatable.All
    type NumberLike = ParameterOperatable.NumberLike
    type Sets = ParameterOperatable.Sets
    type BooleanLike = ParameterOperatable.BooleanLike
    type Number = ParameterOperatable.Number

    @property
    def domain(self) -> Domain:
        return self._domain

    def has_implicit_constraint(self) -> bool:
        return False

    def has_implicit_constraints_recursive(self) -> bool:
        return False

    @once
    def compact_repr(
        self,
        context: ParameterOperatable.ReprContext | None = None,
        use_name: bool = False,
    ) -> str:
        """
        Unit only printed if not dimensionless.

        Letters:
        ```
        A-Z, a-z, α-ω
        A₁-Z₁, a₁-z₁, α₁-ω₁
        A₂-Z₂, a₂-z₂, α₂-ω₂
        ...
        ```
        """

        def param_id_to_human_str(param_id: int) -> str:
            assert isinstance(param_id, int)
            alphabets = [("A", 26), ("a", 26), ("α", 25)]
            alphabet = [
                chr(ord(start_char) + i)
                for start_char, char_cnt in alphabets
                for i in range(char_cnt)
            ]

            def int_to_subscript(i: int) -> str:
                if i == 0:
                    return ""
                _str = str(i)
                return "".join(chr(ord("₀") + ord(c) - ord("0")) for c in _str)

            return alphabet[param_id % len(alphabet)] + int_to_subscript(
                param_id // len(alphabet)
            )

        if use_name and self.get_parent() is not None:
            letter = self.get_full_name()
        else:
            if context is None:
                context = ParameterOperatable.ReprContext()
            if self not in context.variable_mapping.mapping:
                next_id = context.variable_mapping.next_id
                context.variable_mapping.mapping[self] = next_id
                context.variable_mapping.next_id += 1
            letter = param_id_to_human_str(context.variable_mapping.mapping[self])

        unitstr = f" {self.units}" if self.units != dimensionless else ""

        out = f"{letter}{unitstr}"
        out += self._get_lit_suffix()

        return out

    def domain_set(self) -> P_Set:
        return self.domain.unbounded(self)

    def get_last_known_deduced_superset(self, solver: "Solver") -> P_Set | None:
        as_literal = solver.inspect_get_known_supersets(self)
        return None if as_literal == self.domain_set() else as_literal


p_field = f_field(Parameter)

# Canonical ----------------------------------------------------------------------------
CanonicalNumericExpression = Add | Multiply | Power | Round | Abs | Sin | Log
CanonicalLogicExpression = Or | Not
CanonicalSeticExpression = Intersection | Union | SymmetricDifference
CanonicalPredicate = GreaterOrEqual | IsSubset | Is | GreaterThan | IsBitSet
CanonicalOther = IfThenElse

CanonicalConstrainableExpression = CanonicalLogicExpression | CanonicalPredicate

CanonicalExpression = (
    CanonicalNumericExpression
    | CanonicalLogicExpression
    | CanonicalSeticExpression
    | CanonicalPredicate
    | CanonicalOther
)
CanonicalNumber = Quantity_Interval_Disjoint | Quantity_Set_Discrete
CanonicalBoolean = BoolSet
CanonicalEnum = P_Set[Enum]
# TODO Canonical set?

CanonicalLiteral = CanonicalNumber | CanonicalBoolean | CanonicalEnum
CanonicalOperable = CanonicalExpression | Parameter
CanonicalAll = CanonicalOperable | CanonicalLiteral

# --------------------------------------------------------------------------------------

Reflexive = Is | IsSubset | GreaterOrEqual
IdempotentExpression = Abs | Round
IdempotentOperands = Or | Union | Intersection
Commutative = Add | Multiply | Or | Union | Intersection | SymmetricDifference | Is
UnaryIdentity = Add | Multiply | Or | Union | Intersection
FullyAssociative = Add | Multiply | Or | Union | Intersection
Associative = FullyAssociative
Involutory = Not

HasSideEffects = IfThenElse

# python help --------------------------------------------------------------------------
CanonicalExpressionR = (
    Add,
    Multiply,
    Power,
    Round,
    Abs,
    Sin,
    Log,
    Or,
    Not,
    Intersection,
    Union,
    SymmetricDifference,
    Is,
    GreaterOrEqual,
    GreaterThan,
    IsSubset,
)
