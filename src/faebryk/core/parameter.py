# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from enum import Enum

from faebryk.core.node import Node, f_field
from faebryk.libs.sets import Range
from faebryk.libs.units import Quantity, Unit, P
from typing import Protocol

logger = logging.getLogger(__name__)

from typing import runtime_checkable

@runtime_checkable
class HasUnit(Protocol):
    unit: Unit

#TODO: prohibit instantiation
class Expression:
    pass

class Arithmetic(Expression):
    def __init__(self, *operands):
        types = [ int, float, Quantity, Parameter, Expression ]
        if any(not type(op) in types for op in operands):
            raise ValueError("operands must be int, float, Quantity, Parameter, or Expression")
        self.operands = operands

class Additive(Arithmetic):
    def __init__(self, *operands):
        super().__init__(*operands)
        units = [ op.unit if isinstance(op, HasUnit) else P.dimensionless for op in operands ]
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
        self.unit = math.prod([ op.unit if isinstance(op, HasUnit) else P.dimensionless for op in operands ])

class Divide(Multiply):
    def __init__(self, numerator, denominator):
        super().__init__(numerator, denominator)
        self.unit = numerator.unit / denominator.unit


class Domain:
    pass

class Domains:
    class ESeries(Domain):
        class E96(Domain):
            pass

        class E24(Domain):
            pass

    class Numbers(Domain):
        def __init__(self, *, negative: bool = True, zero_allowed: bool = True) -> None:
            super().__init__()
            self.negative = negative
            self.zero_allowed = zero_allowed

        class Integers(Domain):
            class Positive(Domain):
                pass

    class Boolean(Domain):
        pass

    class Enum(Domain):
        def __init__(self, enum_t: type[Enum]):
            super().__init__()
            self.enum_t = enum_t


class Parameter(Node):
    def __init__(
        self,
        *,
        unit: Unit | Quantity,
        # hard constraints
        within: Range | None = None,
        domain: Domain = Domains.Numbers.Reals.Positive(),
        # soft constraints
        soft_set: Range| None = None,
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


p_field = f_field(Parameter)
