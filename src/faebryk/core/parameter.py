# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto
from types import NotImplementedType
from typing import Any, Callable, Protocol

from faebryk.core.core import Namespace
from faebryk.core.node import Node, f_field
from faebryk.libs.sets import Range, Set_
from faebryk.libs.units import HasUnit, Quantity, Unit, dimensionless
from faebryk.libs.util import abstract

logger = logging.getLogger(__name__)


class ParameterOperatable(Protocol):
    type QuantityLike = Quantity | NotImplementedType
    type Number = int | float | QuantityLike

    type NumberLike = ParameterOperatable | Number | Set_[Number]
    type BooleanLike = ParameterOperatable | bool | Set_[bool]
    type EnumLike = ParameterOperatable | Enum | Set_[Enum]

    type All = NumberLike | BooleanLike | EnumLike
    type Sets = All

    def alias_is(self, other: All): ...

    def constrain_le(self, other: NumberLike): ...

    def constrain_ge(self, other: NumberLike): ...

    def constrain_lt(self, other: NumberLike): ...

    def constrain_gt(self, other: NumberLike): ...

    def constrain_ne(self, other: NumberLike): ...

    def constrain_subset(self, other: Sets): ...

    def constrain_superset(self, other: Sets): ...

    def constrain_cardinality(self, other: int): ...

    def operation_add(self, other: NumberLike) -> "Expression": ...

    def operation_subtract(self, other: NumberLike) -> "Expression": ...

    def operation_multiply(self, other: NumberLike) -> "Expression": ...

    def operation_divide(self: NumberLike, other: NumberLike) -> "Expression": ...

    def operation_power(self, other: NumberLike) -> "Expression": ...

    def operation_log(self) -> "Expression": ...

    def operation_sqrt(self) -> "Expression": ...

    def operation_abs(self) -> "Expression": ...

    def operation_floor(self) -> "Expression": ...

    def operation_ceil(self) -> "Expression": ...

    def operation_round(self) -> "Expression": ...

    def operation_sin(self) -> "Expression": ...

    def operation_cos(self) -> "Expression": ...

    def operation_union(self, other: Sets) -> "Expression": ...

    def operation_intersection(self, other: Sets) -> "Expression": ...

    def operation_difference(self, other: Sets) -> "Expression": ...

    def operation_symmetric_difference(self, other: Sets) -> "Expression": ...

    def operation_and(self, other: BooleanLike) -> "Expression": ...

    def operation_or(self, other: BooleanLike) -> "Expression": ...

    def operation_not(self) -> "Expression": ...

    def operation_xor(self, other: BooleanLike) -> "Expression": ...

    def operation_implies(self, other: BooleanLike) -> "Expression": ...

    def operation_is_le(self, other: NumberLike) -> "Expression": ...

    def operation_is_ge(self, other: NumberLike) -> "Expression": ...

    def operation_is_lt(self, other: NumberLike) -> "Expression": ...

    def operation_is_gt(self, other: NumberLike) -> "Expression": ...

    def operation_is_ne(self, other: NumberLike) -> "Expression": ...

    def operation_is_subset(self, other: Sets) -> "Expression": ...

    def operation_is_superset(self, other: Sets) -> "Expression": ...

    def get_any_single(self) -> Number | Enum: ...

    # ----------------------------------------------------------------------------------
    def __add__(self, other: NumberLike):
        return self.operation_add(other)

    def __radd__(self, other: NumberLike):
        return self.operation_add(other)

    def __sub__(self, other: NumberLike):
        # TODO could be set difference
        return self.operation_subtract(other)

    def __rsub__(self, other: NumberLike):
        return self.operation_subtract(other)

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

    # TODO: move

    def if_then_else(
        self,
        if_true: Callable[[], Any],
        if_false: Callable[[], Any],
    ) -> None: ...

    # TODO
    # def switch_case(
    #    self,
    #    cases: list[tuple[?, Callable[[], Any]]],
    # ) -> None: ...


@abstract
class Expression(Node, ParameterOperatable):
    pass


class Arithmetic(HasUnit, Expression):
    def __init__(self, *operands):
        types = [int, float, Quantity, Parameter, Arithmetic]
        if any(type(op) not in types for op in operands):
            raise ValueError(
                "operands must be int, float, Quantity, Parameter, or Expression"
            )
        if any(
            param.domain not in [Numbers, ESeries]
            for param in operands
            if isinstance(param, Parameter)
        ):
            raise ValueError("parameters must have domain Numbers or ESeries")
        self.operands = operands


class Additive(Arithmetic):
    def __init__(self, *operands):
        super().__init__(*operands)
        units = [
            op.units if isinstance(op, HasUnit) else dimensionless for op in operands
        ]
        self.units = units[0]
        if not all(u.is_compatible_with(self.units) for u in units):
            raise ValueError("All operands must have compatible units")


class Add(Additive):
    def __init__(self, *operands):
        super().__init__(*operands)


class Subtract(Additive):
    def __init__(self, *operands):
        super().__init__(*operands)


class Multiply(Arithmetic):
    def __init__(self, *operands):
        super().__init__(*operands)
        units = [
            op.units if isinstance(op, HasUnit) else dimensionless for op in operands
        ]
        self.units = units[0]
        for u in units[1:]:
            self.units *= u


class Divide(Multiply):
    def __init__(self, numerator, denominator):
        super().__init__(numerator, denominator)
        self.units = numerator.units / denominator.units


class Sqrt(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        self.units = operand.units**0.5


class Power(Arithmetic):
    def __init__(self, base, exponent: int):
        super().__init__(base, exponent)
        if isinstance(exponent, HasUnit) and not exponent.units.is_compatible_with(
            dimensionless
        ):
            raise ValueError("exponent must have dimensionless unit")
        units = base.units**exponent if isinstance(base, HasUnit) else dimensionless
        assert isinstance(units, Unit)
        self.units = units


class Log(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        if not operand.unit.is_compatible_with(dimensionless):
            raise ValueError("operand must have dimensionless unit")
        self.units = dimensionless


class Sin(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        if not operand.unit.is_compatible_with(dimensionless):
            raise ValueError("operand must have dimensionless unit")
        self.units = dimensionless


class Cos(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        if not operand.unit.is_compatible_with(dimensionless):
            raise ValueError("operand must have dimensionless unit")
        self.units = dimensionless


class Abs(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        self.units = operand.units


class Round(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        self.units = operand.units


class Floor(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        self.units = operand.units


class Ceil(Arithmetic):
    def __init__(self, operand):
        super().__init__(operand)
        self.units = operand.units


class Logic(Expression):
    def __init__(self, *operands):
        types = [bool, Parameter, Logic, Predicate]
        if any(type(op) not in types for op in operands):
            raise ValueError("operands must be bool, Parameter, Logic, or Predicate")
        if any(
            param.domain != Boolean or not param.units.is_compatible_with(dimensionless)
            for param in operands
            if isinstance(param, Parameter)
        ):
            raise ValueError("parameters must have domain Boolean without a unit")
        self.operands = operands


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
    def __init__(self, left, right):
        super().__init__(left, right)


class Setic(Expression):
    def __init__(self, *operands):
        super().__init__(*operands)
        types = [Parameter, ParameterOperatable.Sets]
        if any(type(op) not in types for op in operands):
            raise ValueError("operands must be Parameter or Set")
        units = [op.units for op in operands]
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


class Predicate(Expression):
    def __init__(self, left, right):
        l_units = left.units if isinstance(left, HasUnit) else dimensionless
        r_units = right.units if isinstance(right, HasUnit) else dimensionless
        if not l_units.is_compatible_with(r_units):
            raise ValueError("operands must have compatible units")
        self.operands = [left, right]


class NumericPredicate(Predicate):
    def __init__(self, left, right):
        super().__init__(left, right)
        if isinstance(left, Parameter) and left.domain not in [Numbers, ESeries]:
            raise ValueError("left operand must have domain Numbers or ESeries")
        if isinstance(right, Parameter) and right.domain not in [Numbers, ESeries]:
            raise ValueError("right operand must have domain Numbers or ESeries")


class LessThan(NumericPredicate):
    pass


class GreaterThan(NumericPredicate):
    pass


class LessOrEqual(NumericPredicate):
    pass


class GreaterOrEqual(NumericPredicate):
    pass


class NotEqual(Predicate):
    pass


class SeticPredicate(Predicate):
    def __init__(self, left, right):
        super().__init__(left, right)
        types = [Parameter, ParameterOperatable.Sets]
        if any(type(op) not in types for op in self.operands):
            raise ValueError("operands must be Parameter or Set")
        units = [op.units for op in self.operands]
        for u in units[1:]:
            if not units[0].is_compatible_with(u):
                raise ValueError("all operands must have compatible units")
        # TODO domain?


class IsSubset(SeticPredicate):
    pass


class IsSuperset(SeticPredicate):
    pass


class Alias(Expression):
    pass


class Is(Alias):
    pass


class Aliases(Namespace):
    IS = Is


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


class Parameter(Node, ParameterOperatable):
    def __init__(
        self,
        *,
        units: Unit | Quantity | None = dimensionless,
        # hard constraints
        within: Range | None = None,
        domain: Domain = Numbers(negative=False),
        # soft constraints
        soft_set: Range | None = None,
        guess: Quantity
        | int
        | float
        | None = None,  # TODO actually allowed to be anything from domain
        tolerance_guess: Quantity | None = None,
        # hints
        likely_constrained: bool = False,
        cardinality: int | None = None,
    ):
        super().__init__()
        if within is None:
            within = Range()
        if not within.units.is_compatible_with(units):
            raise ValueError("incompatible units")

        if not isinstance(units, Unit):
            raise TypeError("units must be a Unit")
        self.units = units
        self.within = within
        self.domain = domain
        self.soft_set = soft_set
        self.guess = guess
        self.tolerance_guess = tolerance_guess
        self.likely_constrained = likely_constrained
        self.cardinality = cardinality

    # ----------------------------------------------------------------------------------
    # TODO implement ParameterOperatable functions
    # ----------------------------------------------------------------------------------


p_field = f_field(Parameter)
