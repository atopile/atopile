# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto
from types import NotImplementedType
from typing import Any, Callable, Self

from faebryk.core.core import Namespace
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.node import Node, f_field
from faebryk.libs.sets import Empty, P_Set, Range, Ranges
from faebryk.libs.units import HasUnit, Quantity, Unit, dimensionless
from faebryk.libs.util import abstract

logger = logging.getLogger(__name__)


# When we make this generic, two types, type T of elements, and type S of known subsets
# boolean: T == S == bool
# enum: T == S == Enum
# number: T == Number type, S == Range[Number]
class ParameterOperatable:
    type QuantityLike = Quantity | NotImplementedType
    type Number = int | float | QuantityLike

    type NonParamNumber = Number | P_Set[Number]
    type NumberLike = ParameterOperatable | NonParamNumber
    type NonParamBoolean = bool | P_Set[bool]
    type BooleanLike = ParameterOperatable | NonParamBoolean
    type NonParamEnum = Enum | P_Set[Enum]
    type EnumLike = ParameterOperatable | NonParamEnum

    type All = NumberLike | BooleanLike | EnumLike
    type NonParamSet = NonParamNumber | NonParamBoolean | NonParamEnum
    type Sets = All

    operated_on: GraphInterface

    def operation_add(self, other: NumberLike) -> "Expression":
        return Add(self, other)

    def operation_subtract(self, other: NumberLike) -> "Expression":
        return Subtract(minuend=self, subtrahend=other)

    def operation_multiply(self, other: NumberLike) -> "Expression":
        return Multiply(self, other)

    def operation_divide(self: NumberLike, other: NumberLike) -> "Expression":
        return Divide(numerator=self, denominator=other)

    def operation_power(self, other: NumberLike) -> "Expression":
        return Power(base=self, exponent=other)

    def operation_log(self) -> "Expression":
        return Log(self)

    def operation_sqrt(self) -> "Expression":
        return Sqrt(self)

    def operation_abs(self) -> "Expression":
        return Abs(self)

    def operation_floor(self) -> "Expression":
        return Floor(self)

    def operation_ceil(self) -> "Expression":
        return Ceil(self)

    def operation_round(self) -> "Expression":
        return Round(self)

    def operation_sin(self) -> "Expression":
        return Sin(self)

    def operation_cos(self) -> "Expression":
        return Cos(self)

    def operation_union(self, other: Sets) -> "Expression":
        return Union(self, other)

    def operation_intersection(self, other: Sets) -> "Expression":
        return Intersection(self, other)

    def operation_difference(self, other: Sets) -> "Expression":
        return Difference(minuend=self, subtrahend=other)

    def operation_symmetric_difference(self, other: Sets) -> "Expression":
        return SymmetricDifference(self, other)

    def operation_and(self, other: BooleanLike) -> "Logic":
        return And(self, other)

    def operation_or(self, other: BooleanLike) -> "Logic":
        return Or(self, other)

    def operation_not(self) -> "Logic":
        return Not(self)

    def operation_xor(self, other: BooleanLike) -> "Logic":
        return Xor(left=self, right=other)

    def operation_implies(self, other: BooleanLike) -> "Logic":
        return Implies(condition=self, implication=other)

    def operation_is_le(self, other: NumberLike) -> "NumericPredicate":
        return LessOrEqual(constraint=False, left=self, right=other)

    def operation_is_ge(self, other: NumberLike) -> "NumericPredicate":
        return GreaterOrEqual(constraint=False, left=self, right=other)

    def operation_is_lt(self, other: NumberLike) -> "NumericPredicate":
        return LessThan(constraint=False, left=self, right=other)

    def operation_is_gt(self, other: NumberLike) -> "NumericPredicate":
        return GreaterThan(constraint=False, left=self, right=other)

    def operation_is_ne(self, other: NumberLike) -> "NumericPredicate":
        return NotEqual(constraint=False, left=self, right=other)

    def operation_is_subset(self, other: Sets) -> "SeticPredicate":
        return IsSubset(constraint=False, left=self, right=other)

    def operation_is_superset(self, other: Sets) -> "SeticPredicate":
        return IsSuperset(constraint=False, left=self, right=other)

    # TODO implement
    def inspect_known_min(self: NumberLike) -> Number:
        return 1 / 0
        # raise NotImplementedError()

    def inspect_known_max(self: NumberLike) -> Number:
        return 1 / 0
        # raise NotImplementedError()

    def inspect_known_values(self: BooleanLike) -> P_Set[bool]:
        return 1 / 0
        # raise NotImplementedError()

    # Run by the solver on finalization
    inspect_final: Callable[[Self], None] = lambda _: None

    def inspect_add_on_final(self, fun: Callable[[Self], None]) -> None:
        current = self.inspect_final

        def new(self2):
            current(self2)
            fun(self2)

        self.inspect_final = new

    # def inspect_num_known_supersets(self) -> int: ...
    # def inspect_get_known_supersets(self) -> Iterable[P_Set]: ...

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


class Constrainable:
    type All = ParameterOperatable.All
    type Sets = ParameterOperatable.Sets
    type NumberLike = ParameterOperatable.NumberLike

    constraints: GraphInterface

    def _constrain(self, constraint: "Predicate"):
        self.constraints.connect(constraint.constrains)

    def alias_is(self, other: All):
        self._constrain(Is(constraint=True, left=self, right=other))

    def constrain_le(self, other: NumberLike):
        self._constrain(LessOrEqual(constraint=True, left=self, right=other))

    def constrain_ge(self, other: NumberLike):
        self._constrain(GreaterOrEqual(constraint=True, left=self, right=other))

    def constrain_lt(self, other: NumberLike):
        self._constrain(LessThan(constraint=True, left=self, right=other))

    def constrain_gt(self, other: NumberLike):
        self._constrain(GreaterThan(constraint=True, left=self, right=other))

    def constrain_ne(self, other: NumberLike):
        self._constrain(NotEqual(constraint=True, left=self, right=other))

    def constrain_subset(self, other: Sets):
        self._constrain(IsSubset(constraint=True, left=self, right=other))

    def constrain_superset(self, other: Sets):
        self._constrain(IsSuperset(constraint=True, left=self, right=other))

    def constrain_cardinality(self, other: int):
        self._constrain(Cardinality(constraint=True, left=self, right=other))

    # shortcuts
    def constraint_true(self):
        self.alias_is(True)

    def constraint_false(self):
        self.alias_is(False)


@abstract
class Expression(Node, ParameterOperatable):
    operates_on: GraphInterface
    operated_on: GraphInterface

    def __init__(self, *operands: ParameterOperatable.All):
        super().__init__()
        self.operatable_operands = {
            op for op in operands if isinstance(op, (Parameter, Expression))
        }

    def __preinit__(self):
        for op in self.operatable_operands:
            self.operates_on.connect(op.operated_on)


@abstract
class ConstrainableExpression(Expression, Constrainable):
    constraints: GraphInterface


@abstract
class Arithmetic(ConstrainableExpression, HasUnit):
    def __init__(self, *operands: ParameterOperatable.NumberLike):
        super().__init__(*operands)
        types = [int, float, Quantity, Parameter, Arithmetic]
        if any(type(op) not in types for op in operands):
            raise ValueError(
                "operands must be int, float, Quantity, Parameter, or Expression"
            )
        if any(
            not isinstance(param.domain, (Numbers, ESeries))
            for param in operands
            if isinstance(param, Parameter)
        ):
            raise ValueError("parameters must have domain Numbers or ESeries")
        self.operands = operands


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


class Subtract(Additive):
    def __init__(self, minuend, subtrahend):
        super().__init__(minuend, subtrahend)


class Multiply(Arithmetic):
    def __init__(self, *operands):
        super().__init__(*operands)
        units = [HasUnit.get_units_or_dimensionless(op) for op in operands]
        self.units = units[0]
        for u in units[1:]:
            self.units *= u


class Divide(Arithmetic):
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
        units = HasUnit.get_units_or_dimensionless(base) ** exponent
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


class Logic(ConstrainableExpression):
    def __init__(self, *operands):
        super().__init__(*operands)
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
    def __init__(self, condition, implication):
        super().__init__(condition, implication)


class IfThenElse(Expression):
    def __init__(self, condition, if_true, if_false, preference: bool | None = None):
        super().__init__(condition)
        self.preference = preference
        self.if_true = if_true
        self.if_false = if_false


class Setic(ConstrainableExpression):
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
    constrains: GraphInterface

    def __init__(self, constraint: bool, left, right):
        super().__init__(left, right)
        self._constraint = constraint
        l_units = HasUnit.get_units_or_dimensionless(left)
        r_units = HasUnit.get_units_or_dimensionless(right)
        if not l_units.is_compatible_with(r_units):
            raise ValueError("operands must have compatible units")
        self.operands = [left, right]

    def constrain(self):
        self._constraint = True

    def is_constraint(self):
        return self._constraint

    # def run_when_known(self, f: Callable[[bool], None]):
    #    getattr(self, "run_when_known_funcs", []).append(f)


class NumericPredicate(Predicate):
    def __init__(self, constraint: bool, left, right):
        super().__init__(constraint, left, right)
        if isinstance(left, Parameter) and not isinstance(
            left.domain, (Numbers, ESeries)
        ):
            raise ValueError(
                "left operand must have domain Numbers or ESeries,"
                f" not {type(left.domain)}"
            )
        if isinstance(right, Parameter) and not isinstance(
            right.domain, (Numbers, ESeries)
        ):
            raise ValueError(
                "right operand must have domain Numbers or ESeries,"
                f" not {type(right.domain)}"
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
    def __init__(self, constraint: bool, left, right):
        super().__init__(constraint, left, right)
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


class Cardinality(SeticPredicate):
    pass


class Is(Predicate):
    def __init__(self, constraint: bool, left, right):
        super().__init__(constraint, left, right)


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


class Parameter(Node, ParameterOperatable, Constrainable):
    def __init__(
        self,
        *,
        units: Unit | Quantity | None = dimensionless,
        # hard constraints
        within: Ranges | Range | None = None,
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
            within = Empty(units)
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

    # Type forwards
    type All = ParameterOperatable.All
    type NumberLike = ParameterOperatable.NumberLike
    type Sets = ParameterOperatable.Sets
    type BooleanLike = ParameterOperatable.BooleanLike
    type Number = ParameterOperatable.Number

    constraints: GraphInterface
    operated_on: GraphInterface


p_field = f_field(Parameter)
