# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F


class ElectricPower(fabll.Node):
    """
    ElectricPower is a class that represents a power rail. Power rails have a
    higher potential (hv), and lower potential (lv) Electrical.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    hv = F.Electrical.MakeChild()
    lv = F.Electrical.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll._ChildField(fabll.is_interface)

    voltage = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Volt,
    )
    max_current = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Ampere,
    )

    bus_max_current_consumption_sum = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Ampere,
    )

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import ElectricPower

        power_5v = new ElectricPower
        assert power_5v.voltage within 5V +/- 5%
        assert power_5v.max_current <= 1A

        # Connect 2 ElectricPowers together
        power_5v ~ ic.power_input

        # Connect an example bypass capacitor
        power_5v.hv ~> example_capacitor ~> power_5v.lv
        """,
        language=F.has_usage_example.Language.ato,
    )
