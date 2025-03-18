# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest

import faebryk.library._F as F  # noqa: F401
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.libs.kicad.fileformats_latest import C_kicad_pcb_file
from faebryk.libs.test.fileformats import PCBFILE
from faebryk.libs.util import find


class TestTransformer(unittest.TestCase):
    def test_bbox(self):
        pcb = C_kicad_pcb_file.loads(PCBFILE)
        fp = find(
            pcb.kicad_pcb.footprints, lambda f: f.propertys["Reference"].value == "R1"
        )
        bbox_pads = PCB_Transformer.get_footprint_pads_bbox(fp)
        self.assertEqual(bbox_pads, ((-0.715, -0.27), (0.715, 0.27)))

        bbox_silk = PCB_Transformer.get_footprint_silkscreen_bbox(fp)
        self.assertEqual(bbox_silk, ((-0.94, -0.5), (0.94, 0.5)))
