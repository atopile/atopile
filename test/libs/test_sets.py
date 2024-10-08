# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest
from pint import DimensionalityError

from faebryk.libs.sets import Range
from faebryk.libs.units import P


def test_range_intersection_simple():
    x = Range(0, 10)
    y = x.intersection(Range(5, 15))
    assert y == Range(5, 10)


def test_range_intersection_empty():
    x = Range(0, 10)
    y = x.intersection(Range(15, 20))
    assert y == Range(empty=True)


def test_range_unit_none():
    x = Range(0, 10)
    assert x.is_compatible_with_unit(P.V)


def test_range_unit_same():
    y = Range(0 * P.V, 10 * P.V)
    assert y.is_compatible_with_unit(P.V)


def test_range_unit_different():
    with pytest.raises(DimensionalityError):
        Range(0 * P.V, 10 * P.A)
