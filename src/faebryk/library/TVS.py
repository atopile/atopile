# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class TVS(F.Diode):
    reverse_breakdown_voltage = L.p_field(units=P.V)

    # @L.rt_field
    # def pickable(self):
    #     return F.is_pickable_by_type(
    #         F.is_pickable_by_type.Type.TVS,
    #         {
    #             "forward_voltage": self.forward_voltage,
    #             "reverse_working_voltage": self.reverse_working_voltage,
    #             "reverse_leakage_current": self.reverse_leakage_current,
    #             "max_current": self.max_current,
    #             "reverse_breakdown_voltage": self.reverse_breakdown_voltage,
    #         },
    #     )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import TVS, ElectricPower, Electrical

        tvs = new TVS
        tvs.reverse_breakdown_voltage = 5.1V +/- 5%
        tvs.max_current = 1A
        tvs.reverse_working_voltage = 5V
        tvs.package = "SOD-123"

        # Connect TVS for power line protection
        power_supply = new ElectricPower
        protected_line = new Electrical

        # TVS protects against voltage spikes
        protected_line ~ tvs.anode
        tvs.cathode ~ power_supply.lv  # Connect to ground

        # Bidirectional TVS for signal line protection
        signal_tvs = new TVS
        signal_tvs.reverse_breakdown_voltage = 3.3V +/- 5%
        signal_line = new Electrical

        signal_line ~ signal_tvs.anode
        signal_tvs.cathode ~ power_supply.lv

        # Common applications: ESD protection, power surge protection
        # TVS clamps voltage spikes to protect sensitive components
        """,
        language=F.has_usage_example.Language.ato,
    )
