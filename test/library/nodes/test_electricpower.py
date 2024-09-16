# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest


class TestFusedPower(unittest.TestCase):
    def test_fused_power(self):
        import faebryk.library._F as F
        from faebryk.libs.units import P

        power_in = F.ElectricPower()
        power_out = F.ElectricPower()

        power_in.voltage.merge(10 * P.V)
        power_in.max_current.merge(500 * P.mA)

        power_in_fused = power_in.fused()

        power_in_fused.connect(power_out)

        fuse = next(iter(power_in_fused.get_children(direct_only=False, types=F.Fuse)))

        self.assertEqual(
            fuse.trip_current.get_most_narrow(), F.Range(0 * P.A, 500 * P.mA)
        )
        self.assertEqual(power_out.voltage.get_most_narrow(), 10 * P.V)
        # self.assertEqual(
        #    power_in_fused.max_current.get_most_narrow(), F.Range(0 * P.A, 500 * P.mA)
        # )
        self.assertEqual(power_out.max_current.get_most_narrow(), F.TBD())
