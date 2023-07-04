# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import unittest

logger = logging.getLogger(__name__)


class TestImportNetlistKicad(unittest.TestCase):
    def test_t2_eq(self):
        with open(
            os.path.join(
                os.path.dirname(__file__), "../../../common/resources/test.net"
            ),
            "r",
        ) as f:
            test_netlist = f.read()

        from faebryk.importers.netlist.kicad.netlist_kicad import to_faebryk_t2_netlist

        to_faebryk_t2_netlist(test_netlist)

        # import pprint
        # pprint.pprint(t2, indent=4)

        # TODO actually test for equality with handbuilt netlist

    def test_t1_eq(self):
        with open(
            os.path.join(
                os.path.dirname(__file__), "../../../common/resources/test.net"
            ),
            "r",
        ) as f:
            test_netlist = f.read()

        from faebryk.exporters.netlist.kicad.netlist_kicad import (
            from_faebryk_t2_netlist,
        )
        from faebryk.exporters.netlist.netlist import make_t2_netlist_from_t1
        from faebryk.importers.netlist.kicad.netlist_kicad import (
            to_faebryk_t1_netlist,
            to_faebryk_t2_netlist,
        )

        t2 = to_faebryk_t2_netlist(test_netlist)
        t1 = to_faebryk_t1_netlist(t2)

        t2p = make_t2_netlist_from_t1(t1)
        from_faebryk_t2_netlist(t2p)

        # import pprint
        # pprint.pprint(k_net, indent=4)

        # TODO actually test for equality with handbuilt netlist


if __name__ == "__main__":
    unittest.main()
