# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest
from pathlib import Path

import faebryk.libs.examples.buildutil as B
from faebryk.libs.kicad.pcb import Project

EXAMPLE_FILES = Path(B.__file__).parent / "resources/example"
PRJFILE = EXAMPLE_FILES / "example.kicad_pro"


class TestPCB(unittest.TestCase):
    def test_project(self):
        p = Project.load(PRJFILE)
        self.assertEqual(p.pcbnew.last_paths.netlist, "../../faebryk/faebryk.net")


if __name__ == "__main__":
    unittest.main()
