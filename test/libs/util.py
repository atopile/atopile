# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest

from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.util import zip_non_locked


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


if __name__ == "__main__":
    setup_basic_logging()
    unittest.main()
