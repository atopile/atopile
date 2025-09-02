# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class GDT(Module):
    common: F.Electrical
    tube_1: F.Electrical
    tube_2: F.Electrical

    dc_breakdown_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(100 * P.V, 1000 * P.V),
    )
    impulse_discharge_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(100 * P.mA, 100 * P.A),
    )

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.tube_1, self.tube_2)

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.GDT
    )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        #pragma experiment("BRIDGE_CONNECT")
        import GDT, Electrical, ElectricPower

        module UsageExample:
            # Power supply to protect
            power_input = new ElectricPower
            protected_power = new ElectricPower
            
            # Gas discharge tube for surge protection
            gdt = new GDT
            gdt.dc_breakdown_voltage = 230V +/- 20%
            gdt.impulse_discharge_current = 10A +/- 20%
            
            # Connect GDT across the power rails for protection
            power_input.hv ~ gdt.tube_1
            power_input.lv ~ gdt.common
            gdt.tube_2 ~ protected_power.lv
            protected_power.hv ~ power_input.hv
        """,
        language=F.has_usage_example.Language.ato,
    )
