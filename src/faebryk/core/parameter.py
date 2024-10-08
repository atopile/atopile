# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from enum import Enum, auto
from typing import Protocol, runtime_checkable

from deprecated import deprecated

from faebryk.core.core import Namespace
from faebryk.core.node import Node, f_field
from faebryk.libs.sets import Range
from faebryk.libs.units import P, Quantity, Unit

logger = logging.getLogger(__name__)


@runtime_checkable
class HasUnit(Protocol):
    unit: Unit


# TODO: prohibit instantiation
class Expression:
    pass


class Arithmetic(Expression):
    def __init__(self, *operands):
        types = [int, float, Quantity, Parameter, Expression]
        if any(type(op) not in types for op in operands):
            raise ValueError(
                "operands must be int, float, Quantity, Parameter, or Expression"
            )
        self.operands = operands


class Additive(Arithmetic):
    def __init__(self, *operands):
        super().__init__(*operands)
        units = [
            op.unit if isinstance(op, HasUnit) else P.dimensionless for op in operands
        ]
        # Check if all units are compatible
        self.unit = units[0]
        if not all(u.is_compatible_with(self.unit) for u in units):
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
        self.unit = math.prod(
            [op.unit if isinstance(op, HasUnit) else P.dimensionless for op in operands]
        )


class Divide(Multiply):
    def __init__(self, numerator, denominator):
        super().__init__(numerator, denominator)
        self.unit = numerator.unit / denominator.unit


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


class Predicate(Node):
    pass


class LessThan(Predicate):
    pass


class GreaterThan(Predicate):
    pass


class LessOrEqual(Predicate):
    pass


class GreaterOrEqual(Predicate):
    pass


class NotEqual(Predicate):
    pass


class IsSubset(Predicate):
    pass


class Alias(Node):
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

    class Domains(Namespace):
        class ESeries(Namespace):
            E6 = lambda: ESeries(ESeries.SeriesType.E6)
            E12 = lambda: ESeries(ESeries.SeriesType.E12)
            E24 = lambda: ESeries(ESeries.SeriesType.E24)
            E48 = lambda: ESeries(ESeries.SeriesType.E48)
            E96 = lambda: ESeries(ESeries.SeriesType.E96)
            E192 = lambda: ESeries(ESeries.SeriesType.E192)

        class Numbers(Namespace):
            REAL = Numbers
            NATURAL = lambda: Numbers(integer=True, negative=False)

        BOOL = Boolean
        ENUM = Enum

    class Expressions(Namespace):
        pass


class Parameter(Node):
    def __init__(
        self,
        *,
        unit: Unit | Quantity,
        # hard constraints
        within: Range | None = None,
        domain: Domain = Numbers(negative=False),
        # soft constraints
        soft_set: Range | None = None,
        guess: Quantity | None = None,
        tolerance_guess: Quantity | None = None,
        # hints
        likely_constrained: bool = False,
    ):
        super().__init__()
        if within is None:
            within = Range()
        if not within.is_compatible_with_unit(unit):
            raise ValueError("incompatible units")

        if not isinstance(unit, Unit):
            raise TypeError("unit must be a Unit")
        self.unit = unit
        self.within = within
        self.domain = domain
        self.soft_set = soft_set
        self.guess = guess
        self.tolerance_guess = tolerance_guess
        self.likely_constrained = likely_constrained

    def alias_is(self, other: "Parameter"):
        pass

    def constrain_le(self, other: "Parameter"):
        pass

    def constrain_ge(self, other: "Parameter"):
        pass

    def constrain_lt(self, other: "Parameter"):
        pass

    def constrain_gt(self, other: "Parameter"):
        pass

    def constrain_ne(self, other: "Parameter"):
        pass

    def constrain_subset(self, other: "Parameter"):
        pass

    @deprecated("use alias_is instead")
    def merge(self, other: "Parameter"):
        return self.alias_is(other)


p_field = f_field(Parameter)
