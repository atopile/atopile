# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest

from pretty import pretty

from faebryk.library.library.components import Resistor
from faebryk.library.library.footprints import SMDTwoPin
from faebryk.library.library.parameters import Constant
from faebryk.library.trait_impl.component import (
    has_defined_footprint,
    has_overriden_name_defined,
    has_symmetric_footprint_pinmap,
)


# Pretty printing does not raise exception
class TestPprint(unittest.TestCase):
    def test_resistor(self):
        r = Resistor(Constant(1))
        r.add_trait(has_defined_footprint(SMDTwoPin(SMDTwoPin.Type._0805)))
        r.add_trait(has_symmetric_footprint_pinmap())
        r.add_trait(has_overriden_name_defined("foo"))
        s = pretty(r)
        print(s)
        self.assertTrue(isinstance(s, str))


if __name__ == "__main__":
    unittest.main()
