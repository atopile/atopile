# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P


class Battery(fabll.Node):
    voltage = fabll.p_field(
        units=P.V,
        soft_set=fabll.Range(0 * P.V, 100 * P.V),
        likely_constrained=True,
    )
    capacity = fabll.p_field(
        units=P.Ah,
        soft_set=fabll.Range(100 * P.mAh, 100 * P.Ah),
        likely_constrained=True,
    )

    power: F.ElectricPower

    def __preinit__(self) -> None:
        self.power.voltage.constrain_subset(self.voltage)

    @fabll.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(self.power)

    designator = fabll.f_field(F.has_designator_prefix)("BAT")

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.power.hv.add(
            F.has_net_name("BAT_VCC", level=F.has_net_name.Level.SUGGESTED)
        )

    usage_example = fabll.f_field(F.has_usage_example)(
        example="""
        import Battery, ElectricPower

        battery = new Battery
        battery.voltage = 3.7V +/- 10%  # Li-ion cell
        battery.capacity = 2000mAh +/- 5%

        # Connect to system power
        system_power = new ElectricPower
        battery.power ~ system_power

        # Battery specifications will constrain system voltage
        assert system_power.voltage within battery.voltage

        # For multiple cells in series
        battery_pack = new Battery
        battery_pack.voltage = 11.1V +/- 10%  # 3S Li-ion pack
        battery_pack.capacity = 2000mAh +/- 5%
        """,
        language=F.has_usage_example.Language.ato,
    )
