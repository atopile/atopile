# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from itertools import pairwise

from faebryk.libs.e_series import (
    E_SERIES_VALUES,
    e_series_intersect,
    e_series_ratio,
)
from faebryk.libs.library import L
from faebryk.libs.units import dimensionless


def test_intersect():
    assert e_series_intersect(L.Range(1, 10), {1, 2, 3}) == L.Singles(1, 2, 3, 10)
    assert e_series_intersect(L.Range(3, 10), {1, 8, 9}) == L.Singles(8, 9, 10)
    assert e_series_intersect(L.Range(10, 1e3), {1, 1.5, 8, 9.9}) == L.Singles(
        10, 15, 80, 99, 100, 150, 800, 990, 1000
    )
    assert e_series_intersect(L.Range(2.1e3, 7.9e3), {1, 2, 8, 9}) == L.Empty(
        units=dimensionless
    )


def test_ratio():
    assert e_series_ratio(
        L.Range(100, 10e3),
        L.Range(100, 10e3),
        L.Single(1 / 5),
        E_SERIES_VALUES.E24,
    ) == (1.2e3, 300)

    assert e_series_ratio(
        L.Range(100, 10e3),
        L.Range(100, 10e3),
        L.Range.from_center(0.0123, 0.0123 / 10),
        E_SERIES_VALUES.E48,
    ) == (9.09e3, 115)


def test_sets():
    E = E_SERIES_VALUES
    EVs24 = [3 * 2**i for i in range(4)]
    EVs192 = [3 * 2**i for i in range(4, 6)]
    for EVs in [EVs24, EVs192]:
        for i1, i2 in pairwise(EVs):
            e1 = getattr(E, f"E{i1}")
            e2 = getattr(E, f"E{i2}")
            assert e1 < e2, f"{i1} < {i2}"
