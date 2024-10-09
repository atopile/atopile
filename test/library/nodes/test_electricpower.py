# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.libs.library import L


def test_fused_power():
    import faebryk.library._F as F
    from faebryk.libs.units import P

    power_in = F.ElectricPower()
    power_out = F.ElectricPower()

    power_in.voltage.constrain_subset(10 * P.V)
    power_in.max_current.constrain_subset(500 * P.mA)

    power_in_fused = power_in.fused()
    power_in_fused.connect(power_out)

    fuse = next(iter(power_in_fused.get_children(direct_only=False, types=F.Fuse)))

    fuse.trip_current.operation_is_subset(
        L.Range.from_center_rel(500 * P.mA, 0.1)
    ).assert_true()
    power_out.voltage.operation_is_subset(10 * P.V).assert_true()
    power_out.max_current.operation_is_le(500 * P.mA * 0.9).assert_true()
