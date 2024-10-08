# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum

from faebryk.core.node import Node, f_field
from faebryk.libs.sets import Range
from faebryk.libs.units import Quantity, Unit

logger = logging.getLogger(__name__)


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

        class Reals(Domain):
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
        within: Range[Quantity] | None = None,
        domain: Domain = Domains.Numbers.Reals.Positive(),
        # soft constraints
        soft_set: Range[Quantity] | None = None,
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

        self.unit = unit
        self.within = within
        self.domain = domain
        self.soft_set = soft_set
        self.guess = guess
        self.tolerance_guess = tolerance_guess
        self.likely_constrained = likely_constrained


p_field = f_field(Parameter)
