# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest

import faebryk.library._F as F
from faebryk.libs.units import P


class TestFootprints(unittest.TestCase):
    def test_qfn_kicad(self):
        test_cases = {
            "Package_DFN_QFN:QFN-16-1EP_4x4mm_P0.5mm_EP2.45x2.45mm_ThermalVias": F.QFN(  # noqa: E501
                pin_cnt=16,
                exposed_thermal_pad_cnt=1,
                size_xy=(4 * P.mm, 4 * P.mm),
                pitch=0.5 * P.mm,
                exposed_thermal_pad_dimensions=(2.45 * P.mm, 2.45 * P.mm),
                has_thermal_vias=True,
            ),
            "Package_DFN_QFN:QFN-12-1EP_3x3mm_P0.5mm_EP1.6x1.6mm": F.QFN(
                pin_cnt=12,
                exposed_thermal_pad_cnt=1,
                size_xy=(3 * P.mm, 3 * P.mm),
                pitch=0.5 * P.mm,
                exposed_thermal_pad_dimensions=(1.6 * P.mm, 1.6 * P.mm),
                has_thermal_vias=False,
            ),
            "Package_DFN_QFN:QFN-20-1EP_3.5x3.5mm_P0.5mm_EP2x2mm": F.QFN(
                pin_cnt=20,
                exposed_thermal_pad_cnt=1,
                size_xy=(3.5 * P.mm, 3.5 * P.mm),
                pitch=0.5 * P.mm,
                exposed_thermal_pad_dimensions=(2 * P.mm, 2 * P.mm),
                has_thermal_vias=False,
            ),
        }

        for solution, footprint in test_cases.items():
            self.assertEqual(
                solution,
                footprint.get_trait(F.has_kicad_footprint).get_kicad_footprint(),
            )

    def test_qfn_constraints(self):
        # test good done in qfn kicad
        # test bad

        # only thermal via if thermal pad cnt > 0
        self.assertRaises(
            AssertionError,
            lambda: F.QFN(
                pin_cnt=20,
                exposed_thermal_pad_cnt=0,
                size_xy=(3.5 * P.mm, 3.5 * P.mm),
                pitch=0.5 * P.mm,
                exposed_thermal_pad_dimensions=(2.5 * P.mm, 2.5 * P.mm),
                has_thermal_vias=True,
            ),
        )

        # pad has to be smaller than package
        self.assertRaises(
            AssertionError,
            lambda: F.QFN(
                pin_cnt=20,
                exposed_thermal_pad_cnt=1,
                size_xy=(3.5 * P.mm, 3.5 * P.mm),
                pitch=0.5 * P.mm,
                exposed_thermal_pad_dimensions=(4.5 * P.mm, 2.5 * P.mm),
                has_thermal_vias=False,
            ),
        )
