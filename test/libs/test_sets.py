# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

from faebryk.libs.library.L import DiscreteSet, EmptySet, Range, RangeWithGaps, Single
from faebryk.libs.units import P, Unit, dimensionless, quantity
from faebryk.libs.util import cast_assert


def test_interval_intersection_simple():
    x = Range(0, 10)
    y = x & Range(5, 15)
    assert y == Range(5, 10)


def test_interval_intersection_empty():
    x = Range(0, 10)
    y = x & Range(15, 20)
    assert y == EmptySet(dimensionless)


def test_interval_unit_none():
    x = Range(0, 10)
    assert not x.units.is_compatible_with(P.V)


def test_interval_unit_same():
    y = Range(0 * P.V, 10 * P.V)
    assert y.units.is_compatible_with(P.V)


def test_interval_unit_different():
    with pytest.raises(ValueError):
        Range(0 * P.V, 10 * P.A)
    with pytest.raises(ValueError):
        Range(0 * P.V, 10 * P.V, units=cast_assert(Unit, P.A))
    with pytest.raises(ValueError):
        Range(max=10 * P.V, units=cast_assert(Unit, P.A))
    with pytest.raises(ValueError):
        Range(min=10 * P.V, units=cast_assert(Unit, P.A))


def test_set_min_elem():
    x = DiscreteSet(5, 3, 2, 4, 1)
    assert x.min_elem() == 1


def test_set_closest_elem():
    x = RangeWithGaps((5, 6), (7, 8), DiscreteSet(2, 4, 1))
    assert x.closest_elem(0 * dimensionless) == 1
    assert x.closest_elem(1 * dimensionless) == 1
    assert x.closest_elem(5.1 * dimensionless) == 5.1 * dimensionless
    assert x.closest_elem(4.9 * dimensionless) == 5 * dimensionless
    assert x.closest_elem(4.1 * dimensionless) == 4 * dimensionless
    assert x.closest_elem(6.9 * dimensionless) == 7 * dimensionless


def test_set_contains():
    x = DiscreteSet(5, 3, 2, 4, 1)
    assert 3 * dimensionless in x
    assert 6 * dimensionless not in x


def test_union_min_elem():
    x = RangeWithGaps(
        (4, 5),
        (3, 7),
        Single(9),
        RangeWithGaps(Range(1, 2), RangeWithGaps(Range(0, 1))),
    )
    assert x.min_elem() == 0


def test_union_contains():
    x = RangeWithGaps(
        (4, 5),
        (3, 7),
        Single(9),
        RangeWithGaps((1, 2), RangeWithGaps((0, 1))),
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

    x = RangeWithGaps(Range(max=1.5 * P.V), Range(2.5 * P.V, 3.5 * P.V))
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
    x = RangeWithGaps(
        EmptySet(dimensionless),
        RangeWithGaps(EmptySet(dimensionless), DiscreteSet(units=dimensionless)),
    )
    assert x.is_empty()


def test_add_empty():
    assert EmptySet(dimensionless) + RangeWithGaps((0, 1)) == EmptySet(dimensionless)


def test_addition():
    assert Range(0, 1) + Range(2, 3) == Range(2, 4)
    assert Range(0, 1) + Single(2) == Range(2, 3)
    assert RangeWithGaps(Single(2), Single(3)) + RangeWithGaps((0, 1)) == Range(2, 4)
    assert RangeWithGaps(Single(10), Range(20, 21)) + RangeWithGaps(
        (0, 1), (100, 101)
    ) == RangeWithGaps((10, 11), (110, 111), (20, 22), (120, 122))


def test_addition_unit():
    assert Range(0 * P.V, 1 * P.V) + Range(2 * P.V, 3 * P.V) == Range(2 * P.V, 4 * P.V)


def test_subtraction():
    assert Range(0, 1) - Range(2, 3) == Range(-3, -1)
    assert Range(0, 1) - Single(2) == Range(-2, -1)


def test_subtraction_unit():
    assert Range(0 * P.V, 1 * P.V) - Range(2 * P.V, 3 * P.V) == Range(
        -3 * P.V, -1 * P.V
    )


def test_multiplication():
    assert Range(0, 2) * Range(2, 3) == Range(0, 6)
    assert Range(0, 1) * Single(2) == Range(0, 2)
    assert Range(0, 1) * Single(-2) == Range(-2, 0)
    assert Range(-1, 1) * Range(2, 4) == Range(-4, 4)
    assert DiscreteSet(0, 1) * DiscreteSet(2, 3) == DiscreteSet(0, 2, 3)
    assert DiscreteSet(0, 1) * DiscreteSet(2, 3) * RangeWithGaps(
        (-1, 0)
    ) == RangeWithGaps((0, 0), (-2, 0), (-3, 0))


def test_multiplication_unit():
    assert Range(0 * P.V, 2 * P.V) * Range(2 * P.A, 3 * P.A) == Range(0 * P.W, 6 * P.W)


def test_invert():
    assert Range(1, 2).op_invert() == Range(0.5, 1)
    assert Range(-2, -1).op_invert() == Range(-1, -0.5)
    assert Range(-1, 1).op_invert() == RangeWithGaps(
        (float("-inf"), -1), (1, float("inf"))
    )
    assert RangeWithGaps((-4, 2), (-1, 3)).op_invert() == RangeWithGaps(
        Range(max=-0.25), Range(min=1 / 3)
    )


def test_invert_unit():
    assert Range(1 * P.V, 2 * P.V).op_invert() == Range(1 / (2 * P.V), 1 / (1 * P.V))


def test_division():
    assert Range(0, 1) / Range(2, 3) == Range(0, 0.5)
    assert Range(0, 1) / Range(0, 3) == Range(min=0.0)


def test_division_unit():
    assert Range(0 * P.V, 1 * P.V) / Range(2 * P.A, 3 * P.A) == Range(
        0 * P.ohm, 1 / 2 * P.ohm
    )


def test_pow():
    assert RangeWithGaps((0, 1), (2, 3)) ** Range(2, 3) == RangeWithGaps(
        (0, 1), (4, 27)
    )


def test_pow_unit():
    assert RangeWithGaps((-3 * P.m, 1 * P.m)) ** Single(quantity(2)) == RangeWithGaps(
        (1 * P.m**2, 9 * P.m**2)
    )


def test_pow_div_eq():
    x = RangeWithGaps(Range(-5, 10))
    y = RangeWithGaps(Range(-2, 3))
    assert x / y == x * y**-1
