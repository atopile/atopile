# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest
from itertools import combinations

from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.util import SharedReference, zip_non_locked


class TestUtil(unittest.TestCase):
    def test_zip_non_locked(self):
        expected = [(1, 4), (2, 5), (3, 6)]

        for val, ref in zip(zip_non_locked([1, 2, 3], [4, 5, 6]), expected):
            self.assertEqual(val, ref)

        expected = [(1, 4), (2, 5), (2, 6)]
        for val, ref in zip((it := zip_non_locked([1, 2, 3], [4, 5, 6])), expected):
            self.assertEqual(val, ref)
            if val == (2, 5):
                it.advance(1)

    def test_shared_reference(self):
        def all_equal(*args: SharedReference):
            for left, right in combinations(args, 2):
                self.assertIs(left.links, right.links)
                self.assertIs(left(), right())
                self.assertEqual(left, right)

        r1 = SharedReference(1)
        r2 = SharedReference(2)

        self.assertEqual(r1(), 1)
        self.assertEqual(r2(), 2)

        r1.link(r2)

        all_equal(r1, r2)

        r3 = SharedReference(3)
        r3.link(r2)

        all_equal(r1, r2, r3)

        r4 = SharedReference(4)
        r5 = SharedReference(5)

        r4.link(r5)

        all_equal(r4, r5)

        r5.link(r1)

        all_equal(r1, r2, r3, r4, r5)


if __name__ == "__main__":
    setup_basic_logging()
    unittest.main()
