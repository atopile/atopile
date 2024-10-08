# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest
from pint import DimensionalityError

from faebryk.libs.sets import Range
from faebryk.libs.units import P, Unit, dimensionless
from faebryk.libs.util import cast_assert


def test_range_intersection_simple():
    x = Range(0, 10)
    y = x.intersection(Range(5, 15))
    assert y == Range(5, 10)


def test_range_intersection_empty():
    x = Range(0, 10)
    y = x.intersection(Range(15, 20))
    assert y == Range(empty=True, units=dimensionless)


def test_range_unit_none():
    x = Range(0, 10)
    assert not x.units.is_compatible_with(P.V)


def test_range_unit_same():
    y = Range(0 * P.V, 10 * P.V)
    assert y.units.is_compatible_with(P.V)


def test_range_unit_different():
    with pytest.raises(DimensionalityError):
        Range(0 * P.V, 10 * P.A)
    with pytest.raises(ValueError):
        Range(0 * P.V, 10 * P.V, units=cast_assert(Unit, P.A))
    with pytest.raises(ValueError):
        Range(max=10 * P.V, units=cast_assert(Unit, P.A))
    with pytest.raises(ValueError):
        Range(min=10 * P.V, units=cast_assert(Unit, P.A))


def test_range_force_unit():
    with pytest.raises(ValueError):
        Range(empty=True)
    with pytest.raises(ValueError):
        Range()
