# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections.abc import Iterable
from enum import Enum, auto
from types import NotImplementedType
from typing import Any, Callable, Self, cast, override

from faebryk.core.core import Namespace
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.node import Node, f_field
from faebryk.core.trait import Trait
from faebryk.libs.sets import P_Set, Range, Ranges
from faebryk.libs.units import HasUnit, Quantity, Unit, dimensionless
from faebryk.libs.util import abstract, cast_assert, find

logger = logging.getLogger(__name__)


# When we make this generic, two types, type T of elements, and type S of known subsets
# boolean: T == S == bool
# enum: T == S == Enum
# number: T == Number type, S == Range[Number]
class ParameterOperatable(Node):
    type QuantityLike = Quantity | Unit | NotImplementedType
    type Number = int | float | QuantityLike

    type NumberLiteral = Number | P_Set[Number]
    type NumberLike = ParameterOperatable | NumberLiteral
    type BooleanLiteral = bool | P_Set[bool]
    type BooleanLike = ParameterOperatable | BooleanLiteral
    type EnumLiteral = Enum | P_Set[Enum]
    type EnumLike = ParameterOperatable | EnumLiteral
    type SetLiteral = NumberLiteral | BooleanLiteral | EnumLiteral

    type All = NumberLike | BooleanLike | EnumLike
    type Literal = NumberLiteral | BooleanLiteral | EnumLiteral | SetLiteral
    type Sets = All

    operated_on: GraphInterface

    def get_operations(self) -> set["Expression"]:
        res = self.operated_on.get_connected_nodes(types=[Expression])
        return cast(set[Expression], res)

    def has_implicit_constraint(self) -> bool:
        raise NotImplementedError()

    def has_implicit_constraints_recursive(self) -> bool:
        raise NotImplementedError()

    @staticmethod
    def sort_by_depth(
        exprs: Iterable["ParameterOperatable"], ascending: bool
    ) -> list["ParameterOperatable"]:
        def key(e: ParameterOperatable):
            if isinstance(e, Expression):
                return e.depth()
            return 0

        return sorted(exprs, key=key, reverse=not ascending)

    def _is_constrains(self) -> list["Is"]:
        return [
            cast_assert(Is, i).get_other_operand(self)
            for i in self.operated_on.get_connected_nodes(types=[Is])
            if cast_assert(Is, i).constrained
        ]

    def obviously_eq(self, other: "ParameterOperatable.All") -> bool:
        if self == other:
            return True
        if other in self._is_constrains():
            return True
        return False

    @staticmethod
    def pops_obviously_eq(a: All, b: All) -> bool:
        if a == b:
            return True
        if isinstance(a, ParameterOperatable):
            return a.obviously_eq(b)
        elif isinstance(b, ParameterOperatable):
            return b.obviously_eq(a)
        return False

    def obviously_eq_hash(self) -> int:
        if hasattr(self, "__hash"):
            return self.__hash

        ises = [i for i in self._is_constrains() if not isinstance(i, Expression)]

        def keyfn(i: Is):
            if isinstance(i, Parameter):
                return 1 << 63
            return hash(i) % (1 << 63)

        sorted_ises = sorted(ises, key=keyfn)
        if len(sorted_ises) > 0:
            self.__hash = hash(sorted_ises[0])
        else:
            self.__hash = id(self)
        return self.__hash

    def operation_add(self, other: NumberLike):
        return Add(self, other)

    def operation_subtract(self: NumberLike, other: NumberLike):
        return Subtract(minuend=self, subtrahend=other)

    def operation_multiply(self, other: NumberLike):
        return Multiply(self, other)

    def operation_divide(self: NumberLike, other: NumberLike):
        return Divide(numerator=self, denominator=other)

    def operation_power(self, other: NumberLike):
        return Power(base=self, exponent=other)

    def operation_log(self):
        return Log(self)

    def operation_sqrt(self):
        return Sqrt(self)

    def operation_abs(self):
        return Abs(self)

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

    def operation_difference(self, other: Sets):
        return Difference(minuend=self, subtrahend=other)

    def operation_symmetric_difference(self, other: Sets):
        return SymmetricDifference(self, other)

    def operation_and(self, other: BooleanLike):
        return And(self, other)

    def operation_or(self, other: BooleanLike):
        return Or(self, other)

    def operation_not(self):
        return Not(self)

    def operation_xor(self, other: BooleanLike):
        return Xor(left=self, right=other)

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

    def operation_is_subset(self, other: Sets):
        return IsSubset(left=self, right=other)

    def operation_is_superset(self, other: Sets):
        return IsSuperset(left=self, right=other)

    # TODO implement
    def inspect_known_min(self: NumberLike) -> Number:
        return HasUnit.get_units_or_dimensionless(self) * float("-inf")
        # raise NotImplementedError()

    def inspect_known_max(self: NumberLike) -> Number:
        return HasUnit.get_units_or_dimensionless(self) * float("inf")
        # raise NotImplementedError()

    def inspect_known_values(self: BooleanLike) -> P_Set[bool]:
        raise Exception("not implemented")
        # raise NotImplementedError()

    # Run by the solver on finalization
    inspect_solution: Callable[[Self], None] = lambda _: None

    def inspect_add_on_solution(self, fun: Callable[[Self], None]) -> None:
        current = self.inspect_solution

        def new(self2):
            current(self2)
            fun(self2)

        self.inspect_solution = new

    # Could be exponentially many
    def inspect_known_supersets_are_few(self) -> bool:
        raise Exception("not implemented")

    def inspect_get_known_supersets(self) -> Iterable[P_Set]:
        raise Exception("not implemented")

    def inspect_get_known_superranges(self: NumberLike) -> Iterable[Ranges]:
        raise Exception("not implemented")

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
        return self.operation_is_lt(other).constrain()

    def constrain_gt(self, other: NumberLike):
        return self.operation_is_gt(other).constrain()

    def constrain_ne(self, other: NumberLike):
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

    # should be eager, in the sense that, if the outcome is known, the callable is
    # called immediately, without storing an expression
    # we must force a value (at the end of solving at the least)
    def if_then_else(
        self,
        if_true: Callable[[], Any],
        if_false: Callable[[], Any],
        preference: bool | None = None,
    ) -> None:
        IfThenElse(self, if_true, if_false, preference)

    # def assert_true(
    #     self, error: Callable[[], None] = lambda: raise_(ValueError())
    # ) -> None:
    #     self.if_then_else(lambda: None, error, True)

    # def assert_false(
    #     self, error: Callable[[], None] = lambda: raise_(ValueError())
    # ) -> None:
    #     self.if_then_else(error, lambda: None, False)

    # TODO
    # def switch_case(
    #    self,
    #    cases: list[tuple[?, Callable[[], Any]]],
    # ) -> None: ...

    # ----------------------------------------------------------------------------------

    def get_operators[T: "Expression"](self, types: type[T] | None = None) -> list[T]:
        if types is None:
            types = Expression  # type: ignore
        types = cast(type[T], types)
        assert issubclass(types, Expression)

        return cast(list[T], self.operated_on.get_connected_nodes(types=[types]))

    def get_literal(self) -> Literal:
        iss = self.get_operators(Is)
        literal_is = find(o for i in iss for o in i.get_literal_operands())
        return literal_is


def has_implicit_constraints_recursive(po: ParameterOperatable.All) -> bool:
    if isinstance(po, ParameterOperatable):
        return po.has_implicit_constraints_recursive()
    return False


@abstract
class Expression(ParameterOperatable):
    operates_on: GraphInterface

    def __init__(self, *operands: ParameterOperatable.All):
        super().__init__()
        self.operands = tuple(operands)
        self.operatable_operands = {
            op for op in operands if isinstance(op, ParameterOperatable)
        }

    def __preinit__(self):
        for op in self.operatable_operands:
            # TODO: careful here, we should make it more clear that operates_on just
            # expresses a relation but is not a replacement of self.operands
            if self.operates_on.is_connected_to(op.operated_on):
                continue
            self.operates_on.connect(op.operated_on)

    def get_operatable_operands(self) -> set[ParameterOperatable]:
        return cast(
            set[ParameterOperatable],
            self.operates_on.get_connected_nodes(types=[ParameterOperatable]),
        )

    def get_literal_operands(self) -> list[ParameterOperatable.Literal]:
        return [o for o in self.operands if not isinstance(o, ParameterOperatable)]

    def depth(self) -> int:
        if hasattr(self, "_depth"):
            return self._depth
        self._depth = 1 + max(
            op.depth() if isinstance(op, Expression) else 0 for op in self.operands
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

    # TODO caching
    @override
    def obviously_eq(self, other: ParameterOperatable.All) -> bool:
        if super().obviously_eq(other):
            return True
        if type(other) is type(self):
            for s, o in zip(self.operands, cast_assert(Expression, other).operands):
                if not ParameterOperatable.pops_obviously_eq(s, o):
                    return False
            return True
        return False

    def obviously_eq_hash(self) -> int:
        return hash((type(self), self.operands))

    def _associative_obviously_eq(self: "Expression", other: "Expression") -> bool:
        remaining = list(other.operands)
        for op in self.operands:
            for r in remaining:
                if ParameterOperatable.pops_obviously_eq(op, r):
                    remaining.remove(r)
                    break
        return not remaining


@abstract
class ConstrainableExpression(Expression):
    def __init__(self, *operands: ParameterOperatable.All):
        super().__init__(*operands)
        self.constrained: bool = False

    def _constrain(self, constraint: "Predicate"):
        constraint.constrain()

    # shortcuts
    def constrain(self):
        self.constrained = True


@abstract
class Arithmetic(Expression):
    def __init__(self, *operands: ParameterOperatable.NumberLike):
        # HasUnit attr
        self.units: Unit = cast(Unit, None)  # checked in postinit

        super().__init__(*operands)
        types = int, float, Quantity, Unit, Parameter, Arithmetic, Ranges, Range
        if any(not isinstance(op, types) for op in operands):
            raise ValueError(
                "operands must be int, float, Quantity, Parameter, or Expression"
            )
        if any(
            not isinstance(param.domain, (Numbers, ESeries))
            for param in operands
            if isinstance(param, Parameter)
        ):
            raise ValueError("parameters must have domain Numbers or ESeries")

    def __postinit__(self):
        assert self.units is not None


@abstract
class Additive(Arithmetic):
    def __init__(self, *operands):
        super().__init__(*operands)
        units = [HasUnit.get_units_or_dimensionless(op) for op in operands]
        self.units = units[0]
        if not all(u.is_compatible_with(self.units) for u in units):
            raise ValueError("All operands must have compatible units")


class Add(Additive):
    def __init__(self, *operands):
        super().__init__(*operands)

    # TODO caching
    @override
    def obviously_eq(self, other: ParameterOperatable.All) -> bool:
        if ParameterOperatable.obviously_eq(self, other):
            return True
        if isinstance(other, Add):
            return self._associative_obviously_eq(other)
        return False

    def obviously_eq_hash(self) -> int:
        op_hash = sum(hash(op) for op in self.operands)
        return hash((type(self), op_hash))

    def has_implicit_constraint(self) -> bool:
        return False


class Subtract(Additive):
    def __init__(self, minuend, subtrahend):
        super().__init__(minuend, subtrahend)

    def has_implicit_constraint(self) -> bool:
        return False


class Multiply(Arithmetic):
    def __init__(self, *operands):
        super().__init__(*operands)
        units = [HasUnit.get_units_or_dimensionless(op) for op in operands]
        self.units = units[0]
        for u in units[1:]:
            self.units = cast_assert(Unit, self.units * u)

    # TODO caching
    @override
    def obviously_eq(self, other: ParameterOperatable.All) -> bool:
        if ParameterOperatable.obviously_eq(self, other):
            return True
        if isinstance(other, Multiply):
            return self._associative_obviously_eq(other)
        return False

    def obviously_eq_hash(self) -> int:
        op_hash = sum(hash(op) for op in self.operands)
        return hash((type(self), op_hash))

    def has_implicit_constraint(self) -> bool:
        return False


class Divide(Arithmetic):
    def __init__(self, numerator, denominator):
        super().__init__(numerator, denominator)
        self.units = HasUnit.get_units_or_dimensionless(
            numerator
        ) / HasUnit.get_units_or_dimensionless(denominator)  # type: ignore

    def has_implicit_constraint(self) -> bool:
        return True  # denominator not zero


class Sqrt(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        self.units = operand.units**0.5

    def has_implicit_constraint(self) -> bool:
        return True  # non-negative


class Power(Arithmetic):
    def __init__(self, base, exponent: int):
        super().__init__(base, exponent)
        if HasUnit.check(exponent) and not HasUnit.get_units(
            exponent
        ).is_compatible_with(dimensionless):
            raise ValueError("exponent must have dimensionless unit")
        units = HasUnit.get_units_or_dimensionless(base) ** exponent
        assert isinstance(units, Unit)
        self.units = units


class Log(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        if not operand.unit.is_compatible_with(dimensionless):
            raise ValueError("operand must have dimensionless unit")
        self.units = dimensionless

    def has_implicit_constraint(self) -> bool:
        return True  # non-negative


class Sin(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        if not operand.unit.is_compatible_with(dimensionless):
            raise ValueError("operand must have dimensionless unit")
        self.units = dimensionless

    def has_implicit_constraint(self) -> bool:
        return False


class Cos(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        if not operand.unit.is_compatible_with(dimensionless):
            raise ValueError("operand must have dimensionless unit")
        self.units = dimensionless

    def has_implicit_constraint(self) -> bool:
        return False


class Abs(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        self.units = operand.units

    def has_implicit_constraint(self) -> bool:
        return False


class Round(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        self.units = operand.units

    def has_implicit_constraint(self) -> bool:
        return False


class Floor(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        self.units = operand.units

    def has_implicit_constraint(self) -> bool:
        return False


class Ceil(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        self.units = operand.units

    def has_implicit_constraint(self) -> bool:
        return False


class Logic(ConstrainableExpression):
    def __init__(self, *operands):
        super().__init__(*operands)
        types = bool, Parameter, Logic, Predicate
        if any(not isinstance(op, types) for op in operands):
            raise ValueError("operands must be bool, Parameter, Logic, or Predicate")
        if any(
            param.domain != Boolean or not param.units.is_compatible_with(dimensionless)
            for param in operands
            if isinstance(param, Parameter)
        ):
            raise ValueError("parameters must have domain Boolean without a unit")


class And(Logic):
    pass


class Or(Logic):
    pass


class Not(Logic):
    def __init__(self, operand):
        super().__init__(operand)


class Xor(Logic):
    def __init__(self, left, right):
        super().__init__(left, right)


class Implies(Logic):
    def __init__(self, condition, implication):
        super().__init__(condition, implication)


class IfThenElse(Expression):
    def __init__(self, condition, if_true, if_false, preference: bool | None = None):
        super().__init__(condition)
        self.preference = preference
        self.if_true = if_true
        self.if_false = if_false


class Setic(Expression):
    def __init__(self, *operands):
        super().__init__(*operands)
        types = [Parameter, ParameterOperatable.Sets]
        if any(type(op) not in types for op in operands):
            raise ValueError("operands must be Parameter or Set")
        units = [HasUnit.get_units_or_dimensionless(op) for op in operands]
        self.units = units[0]
        for u in units[1:]:
            if not self.units.is_compatible_with(u):
                raise ValueError("all operands must have compatible units")
        # TODO domain?


class Union(Setic):
    pass


class Intersection(Setic):
    pass


class Difference(Setic):
    def __init__(self, minuend, subtrahend):
        super().__init__(minuend, subtrahend)


class SymmetricDifference(Setic):
    pass


class Domain:
    pass


class ESeries(Domain):
    class SeriesType(Enum):
        E6 = auto()
        E12 = auto()
        E24 = auto()
        E48 = auto()
        E96 = auto()
        E192 = auto()

    def __init__(self, series: SeriesType):
        self.series = series


class Numbers(Domain):
    def __init__(
        self, *, negative: bool = True, zero_allowed: bool = True, integer: bool = False
    ) -> None:
        super().__init__()
        self.negative = negative
        self.zero_allowed = zero_allowed
        self.integer = integer


class Boolean(Domain):
    pass


class EnumDomain(Domain):
    def __init__(self, enum_t: type[Enum]):
        super().__init__()
        self.enum_t = enum_t


class Predicate(ConstrainableExpression):
    def __init__(self, left, right):
        super().__init__(left, right)
        left, right = self.operands
        l_units = HasUnit.get_units_or_dimensionless(left)
        r_units = HasUnit.get_units_or_dimensionless(right)
        if not l_units.is_compatible_with(r_units):
            raise ValueError("operands must have compatible units")

    def __bool__(self):
        raise ValueError("Predicate cannot be converted to bool")

    def get_other_operand(
        self, operand: ParameterOperatable.All
    ) -> ParameterOperatable.All:
        if self.operands[0] is operand:
            return self.operands[1]
        return self.operands[0]


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
    pass


class GreaterThan(NumericPredicate):
    pass


class LessOrEqual(NumericPredicate):
    pass


class GreaterOrEqual(NumericPredicate):
    pass


class NotEqual(NumericPredicate):
    pass


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
    pass


class IsSuperset(SeticPredicate):
    pass


class Cardinality(SeticPredicate):
    def __init__(
        self, set: ParameterOperatable.Sets, cardinality: ParameterOperatable.NumberLike
    ):
        super().__init__(set, cardinality)


class Is(Predicate):
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
        units: Unit | Quantity | None = dimensionless,
        # hard constraints
        within: Ranges | Range | None = None,
        domain: Domain = Numbers(negative=False),
        # soft constraints
        soft_set: Ranges | Range | None = None,
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

        if isinstance(within, Range):
            within = Ranges(within)

        if isinstance(soft_set, Range):
            soft_set = Ranges(soft_set)

        if not isinstance(units, Unit):
            raise TypeError("units must be a Unit")
        self.units = units
        self.within = within
        self.domain = domain
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

    def has_implicit_constraint(self) -> bool:
        return False

    def has_implicit_constraints_recursive(self) -> bool:
        return False


p_field = f_field(Parameter)
