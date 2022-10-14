# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest
import logging
import os

logger = logging.getLogger("test")


class TestImportSchematicKicad(unittest.TestCase):
    def test_sch_eq(self):
        self.assertTrue(False)

        def load_file(name):
            base_path = os.path.join(
                os.path.dirname(__file__), "../../../../build/kicad6_test/test/"
            )
            # with open(os.path.join(os.path.dirname(__file__), "../../../common/resources/test.kicad_sch"), "r") as f:
            with open(os.path.join(base_path, name), "r") as f:
                return f.read()

        from faebryk.importers.netlist.kicad.schematic_kicad import (
            to_faebryk_t2_netlist,
        )
        from faebryk.exporters.netlist.kicad.netlist_kicad import (
            from_faebryk_t2_netlist,
        )
        from faebryk.exporters.project.faebryk.project_faebryk import from_t1_netlist
        from faebryk.importers.netlist.kicad.netlist_kicad import (
            to_faebryk_t1_netlist as t2_to_t1,
        )

        t2 = to_faebryk_t2_netlist(load_file("test.kicad_sch"), file_loader=load_file)

        print("-" * 80)
        import pprint

        pprint.pprint(t2, indent=4)

        netlist = from_faebryk_t2_netlist(t2)
        assert netlist is not None
        print("-" * 80)
        import pprint

        pprint.pprint(netlist, indent=4)

        from pathlib import Path

        path = Path("./build/faebryk.net")
        logger.info("Writing Experiment netlist to {}".format(path.absolute()))
        path.write_text(netlist)

        t1 = t2_to_t1(t2)
        prj = from_t1_netlist(t1)
        path = Path("./build/faebryk_prj.py")
        path.write_text(prj)

        # TODO actually test for equality with handbuilt netlist


if __name__ == "__main__":
    unittest.main()
