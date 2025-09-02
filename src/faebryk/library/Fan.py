# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class Fan(Module):
    power: F.ElectricPower

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Fan, ElectricPower

        module UsageExample:
            fan = new Fan

            # Connect power supply (typically 12V for PC fans)
            power_12v = new ElectricPower
            assert power_12v.voltage within 12V +/- 5%
            assert power_12v.max_current >= 200mA  # Typical fan current

            fan.power ~ power_12v
        """,
        language=F.has_usage_example.Language.ato,
    )
