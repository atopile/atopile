# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest
from itertools import pairwise

import faebryk.library._F as F
from faebryk.libs.e_series import (
    E_SERIES_VALUES,
    e_series_intersect,
    e_series_ratio,
)


class TestESeries(unittest.TestCase):
    def test_intersect(self):
        self.assertEqual(
            e_series_intersect(F.Range(1, 10), {1, 2, 3}),
            F.Set([F.Constant(1), F.Constant(2), F.Constant(3), F.Constant(10)]),
        )
        self.assertEqual(
            e_series_intersect(F.Range(3, 10), {1, 8, 9}),
            F.Set([F.Constant(8), F.Constant(9), F.Constant(10)]),
        )
        self.assertEqual(
            e_series_intersect(F.Range(10, 1e3), {1, 1.5, 8, 9.9}),
            F.Set(
                [
                    F.Constant(10),
                    F.Constant(15),
                    F.Constant(80),
                    F.Constant(99),
                    F.Constant(100),
                    F.Constant(150),
                    F.Constant(800),
                    F.Constant(990),
                    F.Constant(1000),
                ]
            ),
        )
        self.assertEqual(
            e_series_intersect(F.Range(2.1e3, 7.9e3), {1, 2, 8, 9}),
            F.Set([]),
        )

    def test_ratio(self):
        self.assertEqual(
            e_series_ratio(
                F.Range(100, 10e3),
                F.Range(100, 10e3),
                F.Constant(1 / 5),
                E_SERIES_VALUES.E24,
            ),
            (F.Constant(1.2e3), F.Constant(300)),
        )
        self.assertEqual(
            e_series_ratio(
                F.Range(100, 10e3),
                F.Range(100, 10e3),
                F.Range.from_center(0.0123, 0.0123 / 10),
                E_SERIES_VALUES.E48,
            ),
            (F.Constant(9.09e3), F.Constant(115)),
        )

    def test_sets(self):
        E = E_SERIES_VALUES
        EVs24 = [3 * 2**i for i in range(4)]
        EVs192 = [3 * 2**i for i in range(4, 6)]
        for EVs in [EVs24, EVs192]:
            for i1, i2 in pairwise(EVs):
                e1 = getattr(E, f"E{i1}")
                e2 = getattr(E, f"E{i2}")
                self.assertTrue(e1 < e2, f"{i1} < {i2}")


if __name__ == "__main__":
    unittest.main()
