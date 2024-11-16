# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

from faebryk.libs.sets import (
    Empty,
    Range,
    Ranges,
    Single,
    Singles,
)
from faebryk.libs.units import P, Unit, dimensionless
from faebryk.libs.util import cast_assert


def test_range_intersection_simple():
    x = Range(0, 10)
    y = x.op_intersect_range(Range(5, 15))
    assert y == Range(5, 10)


def test_range_intersection_empty():
    x = Range(0, 10)
    y = x.op_intersect_range(Range(15, 20))
    assert y == Empty(dimensionless)


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


def test_set_min_elem():
    x = Singles(5, 3, 2, 4, 1)
    assert x.min_elem() == 1


def test_set_closest_elem():
    x = Ranges((5, 6), (7, 8), Singles(2, 4, 1))
    assert x.closest_elem(0 * dimensionless) == 1
    assert x.closest_elem(1 * dimensionless) == 1
    assert x.closest_elem(5.1 * dimensionless) == 5.1 * dimensionless
    assert x.closest_elem(4.9 * dimensionless) == 5 * dimensionless
    assert x.closest_elem(4.1 * dimensionless) == 4 * dimensionless
    assert x.closest_elem(6.9 * dimensionless) == 7 * dimensionless


def test_set_contains():
    x = Singles(5, 3, 2, 4, 1)
    assert 3 * dimensionless in x
    assert 6 * dimensionless not in x


def test_union_min_elem():
    x = Ranges(
        (4, 5),
        (3, 7),
        Single(9),
        Ranges(Range(1, 2), Ranges(Range(0, 1))),
    )
    assert x.min_elem() == 0


def test_union_contains():
    x = Ranges(
        (4, 5),
        (3, 7),
        Single(9),
        Ranges((1, 2), Ranges((0, 1))),
    )
    assert 0 * dimensionless in x
    assert 1 * dimensionless in x
    assert 2 * dimensionless in x
    assert 3 * dimensionless in x
    assert 4 * dimensionless in x
    assert 5 * dimensionless in x
    assert 6 * dimensionless in x
    assert 7 * dimensionless in x
    assert 8 * dimensionless not in x
    assert 9 * dimensionless in x
    assert 10 * dimensionless not in x

    x = Ranges(Range(max=1.5 * P.V), Range(2.5 * P.V, 3.5 * P.V))
    assert float("-inf") * P.V in x
    assert 1 * P.V in x
    assert 1.5 * P.V in x
    assert 2 * P.V not in x
    assert 2.5 * P.V in x
    assert 3 * P.V in x
    assert 3.5 * P.V in x
    assert 4 * P.V not in x
    assert float("inf") * P.V not in x
    assert 1 not in x
    assert 1 * dimensionless not in x


def test_union_empty():
    x = Ranges(
        Empty(dimensionless),
        Ranges(Empty(dimensionless), Singles(units=dimensionless)),
    )
    assert x.is_empty()


def test_add_empty():
    assert (Empty(dimensionless).op_add_ranges(Ranges((0, 1)))) == Empty(dimensionless)


def test_addition():
    assert Range(0, 1).op_add_range(Range(2, 3)) == Range(2, 4)
    assert Range(0, 1).op_add_range(Single(2)) == Range(2, 3)
    assert Ranges(Single(2), Single(3)).op_add_ranges(Ranges((0, 1))) == Range(2, 4)
    assert Ranges(Single(10), Range(20, 21)).op_add_ranges(
        Ranges((0, 1), (100, 101))
    ) == Ranges((10, 11), (110, 111), (20, 22), (120, 122))


def test_addition_unit():
    assert Range(0 * P.V, 1 * P.V).op_add_range(Range(2 * P.V, 3 * P.V)) == Range(
        2 * P.V, 4 * P.V
    )


def test_subtraction():
    assert Range(0, 1).op_subtract_range(Range(2, 3)) == Range(-3, -1)
    assert Range(0, 1).op_subtract_range(Single(2)) == Range(-2, -1)


def test_subtraction_unit():
    assert Range(0 * P.V, 1 * P.V).op_subtract_range(Range(2 * P.V, 3 * P.V)) == Range(
        -3 * P.V, -1 * P.V
    )


def test_multiplication():
    assert Range(0, 2).op_mul_range(Range(2, 3)) == Range(0, 6)
    assert Range(0, 1).op_mul_range(Single(2)) == Range(0, 2)
    assert Range(0, 1).op_mul_range(Single(-2)) == Range(-2, 0)
    assert Range(-1, 1).op_mul_range(Range(2, 4)) == Range(-4, 4)
    assert Singles(0, 1).op_mul_ranges(Singles(2, 3)) == Singles(0, 2, 3)
    assert Singles(0, 1).op_mul_ranges(Singles(2, 3)).op_mul_ranges(
        Ranges((-1, 0))
    ) == Ranges((0, 0), (-2, 0), (-3, 0))


def test_multiplication_unit():
    assert Range(0 * P.V, 2 * P.V).op_mul_range(Range(2 * P.A, 3 * P.A)) == Range(
        0 * P.W, 6 * P.W
    )


def test_invert():
    assert Range(1, 2).op_invert() == Range(0.5, 1)
    assert Range(-2, -1).op_invert() == Range(-1, -0.5)
    assert Range(-1, 1).op_invert() == Ranges((float("-inf"), -1), (1, float("inf")))
    assert Ranges((-4, 2), (-1, 3)).op_invert() == Ranges(
        Range(max=-0.25), Range(min=1 / 3)
    )


def test_invert_unit():
    assert Range(1 * P.V, 2 * P.V).op_invert() == Range(1 / (2 * P.V), 1 / (1 * P.V))


def test_division():
    assert Range(0, 1).op_div_range(Range(2, 3)) == Range(0, 0.5)
    assert Range(0, 1).op_div_range(Range(0, 3)) == Range(min=0.0)


def test_division_unit():
    assert Range(0 * P.V, 1 * P.V).op_div_range(Range(2 * P.A, 3 * P.A)) == Range(
        0 * P.ohm, 1 / 2 * P.ohm
    )
