# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import unittest

from faebryk.libs.kicad.sexp import prettify_sexp_string

logger = logging.getLogger(__name__)


class TestImportNetlistKicad(unittest.TestCase):
    def test_simple_netlist_equality(self):
        # TODO instead of using simple netlist, filter it here
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "../../../common/resources/test_essentials.net",
            ),
            "r",
        ) as f:
            test_netlist = f.read()

        from faebryk.exporters.netlist.kicad.netlist_kicad import (
            from_faebryk_t2_netlist,
        )
        from faebryk.importers.netlist.kicad.netlist_kicad import (
            to_faebryk_t2_netlist,
        )

        t2 = to_faebryk_t2_netlist(test_netlist)

        out_netlist = from_faebryk_t2_netlist(t2)

        pretty_test = prettify_sexp_string(test_netlist)
        pretty_out = prettify_sexp_string(out_netlist)

        self.assertEqual(pretty_test, pretty_out)


if __name__ == "__main__":
    unittest.main()
