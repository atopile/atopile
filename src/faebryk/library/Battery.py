# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F


class Battery(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    voltage = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Volt,
    )
    capacity = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.AmpereHour,
    )
    power = F.ElectricPower.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeChild_Trait(fabll.is_module.MakeChild())

    _single_electric_reference = fabll.Traits.MakeChild_Trait(
        fabll.ChildField(F.has_single_electric_reference)
    )

    # TODO: Add trait edge to power.hv
    # _net_name = fabll.Traits.MakeChild_Trait(
    #     F.has_net_name.MakeChild(
    #         name="BAT_VCC",
    #         level=F.has_net_name.Level.SUGGESTED,
    #     ),
    #     [power, "hv"],
    # )

    designator_prefix = fabll.Traits.MakeChild_Trait(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.BAT)
    )

    usage_example = fabll.Traits.MakeChild_Trait(
        F.has_usage_example.MakeChild(
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
        ).put_on_type()
    )
