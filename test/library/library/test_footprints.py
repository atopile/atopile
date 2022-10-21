# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest
import faebryk.library.library.footprints as footprints
from faebryk.library.kicad import has_kicad_footprint


class TestFootprints(unittest.TestCase):
    def test_qfn_kicad(self):
        test_cases = {
            "Package_DFN_QFN:QFN-16-1EP_4x4mm_P0.5mm_EP2.45x2.45mm_ThermalVias": footprints.QFN(
                pin_cnt=16,
                exposed_thermal_pad_cnt=1,
                size_xy_mm=(4, 4),
                pitch_mm=0.5,
                exposed_thermal_pad_dimensions_mm=(2.45, 2.45),
                has_thermal_vias=True,
            ),
            "Package_DFN_QFN:QFN-12-1EP_3x3mm_P0.5mm_EP1.6x1.6mm": footprints.QFN(
                pin_cnt=12,
                exposed_thermal_pad_cnt=1,
                size_xy_mm=(3, 3),
                pitch_mm=0.5,
                exposed_thermal_pad_dimensions_mm=(1.6, 1.6),
                has_thermal_vias=False,
            ),
            "Package_DFN_QFN:QFN-20-1EP_3.5x3.5mm_P0.5mm_EP2x2mm": footprints.QFN(
                pin_cnt=20,
                exposed_thermal_pad_cnt=1,
                size_xy_mm=(3.5, 3.5),
                pitch_mm=0.5,
                exposed_thermal_pad_dimensions_mm=(2, 2),
                has_thermal_vias=False,
            ),
        }

        for solution, footprint in test_cases.items():
            self.assertEqual(
                solution, footprint.get_trait(has_kicad_footprint).get_kicad_footprint()
            )

    def test_qfn_constraints(self):
        # test good done in qfn kicad
        # test bad

        # only thermal via if thermal pad cnt > 0
        self.assertRaises(
            AssertionError,
            lambda: footprints.QFN(
                pin_cnt=20,
                exposed_thermal_pad_cnt=0,
                size_xy_mm=(3.5, 3.5),
                pitch_mm=0.5,
                exposed_thermal_pad_dimensions_mm=(2.5, 2.5),
                has_thermal_vias=True,
            ),
        )

        # pad has to be smaller than package
        self.assertRaises(
            AssertionError,
            lambda: footprints.QFN(
                pin_cnt=20,
                exposed_thermal_pad_cnt=1,
                size_xy_mm=(3.5, 3.5),
                pitch_mm=0.5,
                exposed_thermal_pad_dimensions_mm=(4.5, 2.5),
                has_thermal_vias=False,
            ),
        )


if __name__ == "__main__":
    unittest.main()
