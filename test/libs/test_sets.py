# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import math
from enum import Enum, auto

import pytest

from faebryk.libs.library.L import DiscreteSet, EmptySet, Range, RangeWithGaps, Single
from faebryk.libs.sets.numeric_sets import (
    Numeric_Interval,
    Numeric_Interval_Disjoint,
    float_round,
    rel_round,
)
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
    Quantity_Set_Discrete,
)
from faebryk.libs.sets.sets import BoolSet, EnumSet, P_Set
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
    assert x.min_elem == 1


def test_set_closest_elem():
    x = RangeWithGaps((5, 6), (7, 8), DiscreteSet(2, 4, 1))
    assert x.closest_elem(quantity(0)) == 1
    assert x.closest_elem(quantity(1)) == 1
    assert x.closest_elem(quantity(5.1)) == 5.1
    assert x.closest_elem(quantity(4.9)) == 5
    assert x.closest_elem(quantity(4.1)) == 4
    assert x.closest_elem(quantity(6.9)) == 7


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
    assert x.min_elem == 0


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


@pytest.mark.parametrize(
    "base,exp, expected",
    # [-11, 10]^2 -> [0, 11^2]
    # [-11, 10]^3 -> [-11^3, 10^3]
    # [-11, 10]^[2,3] -> [-11^3, 10^3]
    # [-5, 2]^[2,3] -> [-5^3, -5^2]
    [
        (
            Range(-11, 10),
            Range(2, 2),
            Range(0, 11**2),
        ),
        (
            Range(-11, 10),
            Range(3, 3),
            Range(-(11**3), 10**3),
        ),
        (
            Range(-11, 10),
            DiscreteSet(2, 3),
            Range(-(11**3), 10**3),
        ),
        (
            Range(-5, 2),
            DiscreteSet(2, 3),
            Range(-(5**3), (5**2)),
        ),
    ],
)
def test_pow_extended(
    base: Range,
    exp: Range,
    expected: Range,
):
    base_q, exp_q, expected_q = (
        RangeWithGaps.from_value(base),
        RangeWithGaps.from_value(exp),
        RangeWithGaps.from_value(expected),
    )
    assert base_q**exp_q == expected_q


@pytest.mark.skip(
    "Zero crossing not implemented https://github.com/atopile/atopile/issues/614"
)
def test_pow_unit():
    assert RangeWithGaps((-3 * P.m, 1 * P.m)) ** Single(quantity(2)) == RangeWithGaps(
        (1 * P.m**2, 9 * P.m**2)
    )


@pytest.mark.skip(
    "Zero crossing not implemented https://github.com/atopile/atopile/issues/614"
)
def test_pow_div_eq():
    x = RangeWithGaps(Range(-5, 10))
    y = RangeWithGaps(Range(-2, 3))
    assert x / y == x * y**-1


def test_boolset_contain():
    assert BoolSet(True) in [BoolSet(True), BoolSet(False), BoolSet(True, False)]
    assert BoolSet(False) in [BoolSet(True), BoolSet(False), BoolSet(True, False)]
    assert BoolSet(True) not in [BoolSet(False), BoolSet(True, False)]
    assert BoolSet(False) not in [BoolSet(True), BoolSet(True, False)]
    assert True in [BoolSet(True)]
    assert False in [BoolSet(False)]
    assert True not in [BoolSet(True, False)]
    assert False not in [BoolSet(True, False)]
    assert True in BoolSet(True, False)
    assert False in BoolSet(True, False)


def test_boolset_eq():
    assert BoolSet(True) == BoolSet(True)
    assert BoolSet(False) == BoolSet(False)
    assert BoolSet(True, False) == BoolSet(True, False)
    assert BoolSet(True) != BoolSet(False)
    assert BoolSet(True) != BoolSet(True, False)
    assert True == BoolSet(True)  # noqa: E712
    with pytest.raises(Exception):
        bool(BoolSet(True))
    assert False == BoolSet(False)  # noqa: E712
    assert True != BoolSet(False)  # noqa: E712
    assert False != BoolSet(True)  # noqa: E712
    assert BoolSet(True, False) == BoolSet(False, True)
    assert True is not BoolSet(True)


def test_comparison():
    assert (
        RangeWithGaps((1 * P.V, 2 * P.V)) >= RangeWithGaps((0 * P.V, 1 * P.V))
    ) == BoolSet(True)
    assert (
        RangeWithGaps((1 * P.V, 2 * P.V)) <= RangeWithGaps((2 * P.V, 3 * P.V))
    ) == BoolSet(True)
    assert (
        RangeWithGaps((1 * P.V, 2 * P.V)) >= RangeWithGaps((0 * P.V, 0.5 * P.V))
    ) == BoolSet(True)
    assert (
        RangeWithGaps((1 * P.V, 2 * P.V)) <= RangeWithGaps((2.5 * P.V, 3 * P.V))
    ) == BoolSet(True)

    assert (
        RangeWithGaps((1 * P.V, 2 * P.V)) <= RangeWithGaps((0 * P.V, 0.5 * P.V))
    ) == BoolSet(False)
    assert (
        RangeWithGaps((1 * P.V, 2 * P.V)) >= RangeWithGaps((2.5 * P.V, 3 * P.V))
    ) == BoolSet(False)

    assert (
        RangeWithGaps((1 * P.V, 2 * P.V)) <= RangeWithGaps((0 * P.V, 1 * P.V))
    ) == BoolSet(True, False)
    assert (
        RangeWithGaps((1 * P.V, 2 * P.V)) >= RangeWithGaps((2 * P.V, 3 * P.V))
    ) == BoolSet(True, False)


def test_enumset():
    class E(Enum):
        A = auto()
        B = auto()
        C = auto()

    x = EnumSet(E.B, E.C)
    y = EnumSet(E.A, E.B)
    z = x & y

    assert z.enum.enum is E

    assert E.B in z
    assert E.A not in z

    assert z == EnumSet(E.B)


class _Enum(Enum):
    A = auto()
    B = auto()
    C = auto()


@pytest.mark.parametrize(
    "input_set,expected",
    [
        (Numeric_Interval(-10, 20), None),
        (Numeric_Interval(-10.5, 20.5), None),
        (Numeric_Interval(-10.5, 20), None),
        (Numeric_Interval(-math.inf, 50), None),
        (
            Numeric_Interval_Disjoint(
                Numeric_Interval(-10, 20), Numeric_Interval(30, 40.0)
            ),
            None,
        ),
        (BoolSet(True), None),
        (BoolSet.unbounded(), None),
        (Quantity_Interval_Disjoint(Quantity_Interval(0.0 * P.V, 1.0 * P.V)), None),
        (EnumSet(_Enum.A, _Enum.B), None),
        (EnumSet.unbounded(_Enum), None),
    ],
)
def test_serialize(input_set: P_Set, expected: P_Set | None):
    if expected is None:
        expected = input_set
    serialized = input_set.serialize()
    deserialized = P_Set.deserialize(serialized)
    assert deserialized == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        (1.5, 2),
        (1, 1),
        (math.inf, math.inf),
        (-math.inf, -math.inf),
        (
            Quantity_Interval_Disjoint(Quantity_Interval(1.5, 2.5)),
            Quantity_Interval_Disjoint(Quantity_Interval(2, 2)),
        ),
        (
            Quantity_Interval_Disjoint(Quantity_Interval(1.5, math.inf)),
            Quantity_Interval_Disjoint(Quantity_Interval(2, math.inf)),
        ),
    ],
)
def test_float_round(value, expected):
    assert float_round(value) == expected


def test_regression_ss_zero():
    x = Quantity_Set_Discrete(2.77e-17)
    y = Quantity_Interval_Disjoint(Quantity_Interval(-math.inf, 0))
    assert x.is_subset_of(y)


@pytest.mark.parametrize(
    "digits,expected",
    [
        (0, Quantity_Interval_Disjoint(Quantity_Interval(2, 2))),
        (1, Quantity_Interval_Disjoint(Quantity_Interval(1.5, 2.4))),
        (2, Quantity_Interval_Disjoint(Quantity_Interval(1.51, 2.42))),
    ],
)
def test_round_digits(digits: int, expected: Quantity_Interval_Disjoint):
    x = Quantity_Interval_Disjoint(Quantity_Interval(1.51, 2.42))
    assert round(x, digits) == expected


@pytest.mark.parametrize(
    "value,digits,expected",
    [
        (1234.5678, 2, 1200),
        (1234.5678, 4, 1235),
        (1234.5678, 6, 1234.57),
        (1234.5678, 10, 1234.5678),
        (0.123456, 2, 0.12),
        (0.123456, 4, 0.1235),
        (0.123456, 6, 0.123456),
        (0.123456, 10, 0.123456),
    ],
)
def test_rel_round(value: float | int, digits: int, expected: float | int):
    assert rel_round(value, digits) == expected
