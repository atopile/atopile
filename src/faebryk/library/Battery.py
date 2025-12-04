# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F


class Battery(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power = F.ElectricPower.MakeChild()

    voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    capacity = F.Parameters.NumericParameter.MakeChild(unit=F.Units.AmpereHour)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    power.add_dependant(fabll.Traits.MakeEdge(F.is_lead.MakeChild(), [power, "hv"]))
    power.add_dependant(fabll.Traits.MakeEdge(F.is_lead.MakeChild(), [power, "lv"]))

    _single_electric_reference = fabll.Traits.MakeEdge(
        fabll._ChildField(F.has_single_electric_reference)
    )

    # TODO: Add trait edge to power.hv
    _net_name = fabll.Traits.MakeEdge(
        child_field=F.has_net_name.MakeChild(
            name="BAT_VCC",
            level=F.has_net_name.Level.SUGGESTED,
        ),
        owner=[power, "hv"],
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.BAT)
    )

    usage_example = fabll.Traits.MakeEdge(
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
