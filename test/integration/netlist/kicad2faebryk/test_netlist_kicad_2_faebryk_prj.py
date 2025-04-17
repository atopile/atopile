# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import unittest

import pytest

logger = logging.getLogger(__name__)


@pytest.mark.skip(reason="Not implemented")
class TestNetlistKicad2FaebrykProject(unittest.TestCase):
    def test_eq(self):
        self.assertTrue(False)

        from faebryk.exporters.project.faebryk.project_faebryk import from_t1_netlist
        from faebryk.importers.netlist.kicad.netlist_kicad import (
            to_faebryk_t1_netlist,
            to_faebryk_t2_netlist,
        )

        with open(
            os.path.join(
                os.path.dirname(__file__), "../../../common/resources/test.net"
            ),
            "r",
            encoding="utf-8",
        ) as f:
            test_netlist = f.read()

        t2 = to_faebryk_t2_netlist(test_netlist)
        t1 = to_faebryk_t1_netlist(t2)
        from_t1_netlist(t1)

        # print(prj)

        # from pathlib import Path
        # path = Path("./build/faebryk_prj.py")
        # logger.info("Writing Experiment prj to {}".format(path.absolute()))
        # path.write_text(prj, encoding="utf-8")
