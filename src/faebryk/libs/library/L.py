# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
WARNING: Only use this module in the library and apps!
"""

import logging
from typing import Any

from faebryk.core.module import Module  # noqa: F401
from faebryk.core.moduleinterface import ModuleInterface  # noqa: F401
from faebryk.core.node import (  # noqa: F401
    InitVar,
    Node,
    d_field,
    f_field,
    list_f_field,
    list_field,
    rt_field,
)
from faebryk.core.parameter import R, p_field  # noqa: F401
from faebryk.core.reference import reference  # noqa: F401
from faebryk.core.trait import Trait  # noqa: F401
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
    Quantity_Set_Discrete,
    Quantity_Set_Empty,
    Quantity_Singleton,
    QuantityLike,
    QuantityLikeR,
)
from faebryk.libs.sets.sets import BoolSet, EnumSet  # noqa: F401
from faebryk.libs.units import Unit


class AbstractclassError(Exception): ...


logger = logging.getLogger(__name__)


Predicates = R.Predicates
Domains = R.Domains
Expressions = R.Expressions

# TODO: Pint is really bad with types
# Thus we need to allow everything to avoid type errors all over the place
# This is really annoying and should be fixed in Pint
# 5 * P.V is Quantity | Unknown | PlainQuantity[Any]

type RelaxedQuantity = QuantityLike | Any


class Range(Quantity_Interval):
    def __init__(
        self,
        min: RelaxedQuantity | None = None,
        max: RelaxedQuantity | None = None,
        units: Unit | None = None,
    ):
        if min is not None:
            assert isinstance(min, QuantityLikeR)
        if max is not None:
            assert isinstance(max, QuantityLikeR)
        super().__init__(min, max, units)


class RangeWithGaps(Quantity_Interval_Disjoint):
    def __init__(
        self,
        *intervals: "Quantity_Interval | Quantity_Interval_Disjoint | tuple[RelaxedQuantity, RelaxedQuantity]",  # noqa: E501
        units: Unit | None = None,
    ):
        super().__init__(*intervals, units=units)


class Single(Quantity_Singleton):
    def __init__(self, value: RelaxedQuantity):
        assert isinstance(value, QuantityLikeR)
        super().__init__(value)


class DiscreteSet(Quantity_Set_Discrete):
    def __init__(self, *values: RelaxedQuantity, units: Unit | None = None):
        assert all(isinstance(v, QuantityLikeR) for v in values)
        super().__init__(*values, units=units)


def EmptySet(units: Unit | None = None):
    return Quantity_Set_Empty(units)
