# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest
from pint import DimensionalityError

from faebryk.libs.sets import (
    Range,
    Set,
    Single,
    Union,
    operation_add,
    operation_subtract,
)
from faebryk.libs.units import P, Unit, dimensionless
from faebryk.libs.util import cast_assert


def test_range_intersection_simple():
    x = Range(0, 10)
    y = x.range_intersection(Range(5, 15))
    assert y == Range(5, 10)


def test_range_intersection_empty():
    x = Range(0, 10)
    y = x.range_intersection(Range(15, 20))
    assert y == Range(empty=True, units=dimensionless)


def test_range_unit_none():
    x = Range(0, 10)
    assert not x.units.is_compatible_with(P.V)


def test_range_unit_same():
    y = Range(0 * P.V, 10 * P.V)
    assert y.units.is_compatible_with(P.V)


def test_range_unit_different():
    with pytest.raises(ValueError):
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


def test_set_min_elem():
    x = Set(5, 3, 2, 4, 1)
    assert x.min_elem() == 1


def test_set_contains():
    x = Set(5, 3, 2, 4, 1)
    assert 3 in x
    assert 6 not in x


def test_union_min_elem():
    x = Union(
        Range(4, 5), Range(3, 7), Single(9), Union(Range(1, 2), Union(Range(0, 1)))
    )
    assert x.min_elem() == 0


def test_union_contains():
    x = Union(
        Range(4, 5), Range(3, 7), Single(9), Union(Range(1, 2), Union(Range(0, 1)))
    )
    assert 0 in x
    assert 1 in x
    assert 2 in x
    assert 3 in x
    assert 4 in x
    assert 5 in x
    assert 6 in x
    assert 7 in x
    assert 8 not in x
    assert 9 in x
    assert 10 not in x

    x = Union(Range(max=1.5 * P.V), Range(2.5 * P.V, 3.5 * P.V))
    assert float("-inf") * P.V in x
    assert 1 * P.V in x
    assert 1.5 * P.V in x
    assert 2 * P.V not in x
    assert 2.5 * P.V in x
    assert 3 * P.V in x
    assert 3.5 * P.V in x
    assert 4 * P.V not in x
    assert float("inf") * P.V not in x
    with pytest.raises(ValueError):  # units
        assert 1 not in x


def test_union_empty():
    x = Union(
        Range(empty=True, units=dimensionless),
        Union(Range(empty=True, units=dimensionless), Set(units=dimensionless)),
    )
    assert x.empty


def test_addition():
    assert operation_add(Range(0, 1), Range(2, 3)) == Range(2, 4)
    assert operation_add(Range(0, 1), Single(2), Single(3)) == Range(5, 6)
    assert operation_add(Set(0, 1), Set(2, 3)) == Set(2, 3, 4)
    assert operation_add(Set(0, 1), Set(2, 3), Range(-1, 0)) == Union(
        Range(1, 2), Range(2, 3), Range(3, 4)
    )
    assert operation_add(
        Single(3), Set(0, 1), Set(2, 3), Range(-1, 0), Single(7)
    ) == Union(Range(11, 12), Range(12, 13), Range(13, 14))
    assert operation_add(
        Union(Range(0, 1), Range(2, 3)),
        Union(Range(4, 5), Range(6, 7)),
    ) == Union(Range(4, 6), Range(6, 8), Range(6, 8), Range(8, 10))


def test_subtraction():
    assert operation_subtract(Range(0, 1), Range(2, 3)) == Range(-3, -1)
    assert operation_subtract(Range(0, 1), Single(2)) == Range(-2, -1)
