# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


# TODO: Deprecate, use Diode instead
class TVS(fabll.Node):
    reverse_breakdown_voltage = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Volt)

    usage_example = F.has_usage_example.MakeChild(
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
