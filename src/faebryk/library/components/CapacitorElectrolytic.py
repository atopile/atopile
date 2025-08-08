# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class CapacitorElectrolytic(F.Capacitor):
    attach_to_footprint = None

    anode: F.Electrical
    cathode: F.Electrical

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.CAPACITORS_ELECTROLYTIC,
            params=[self.capacitance, self.max_voltage, self.temperature_coefficient, self.package],
        )

    @L.rt_field
    def has_pin_association_heuristic_lookup_table(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.anode: ["anode", "a"],
                self.cathode: ["cathode", "c"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import CapacitorElectrolytic, ElectricPower

        electrolytic_cap = new CapacitorElectrolytic
        electrolytic_cap.capacitance = 1000uF +/- 20%
        electrolytic_cap.max_voltage = 25V
        electrolytic_cap.package = "radial_8x12"  # 8mm diameter, 12mm height

        # Connect to power supply for bulk filtering
        power_supply = new ElectricPower
        assert power_supply.voltage within 12V +/- 10%

        # CRITICAL: Observe polarity! Anode to positive, cathode to negative
        power_supply.hv ~ electrolytic_cap.anode    # Positive terminal
        power_supply.lv ~ electrolytic_cap.cathode  # Negative terminal

        # Alternative bridge syntax (maintains polarity)
        power_supply.hv ~> electrolytic_cap ~> power_supply.lv

        # Common values and applications:
        # - 10-100uF: Local power supply filtering
        # - 100-1000uF: Bulk power supply capacitance
        # - 1000-10000uF: Main power supply smoothing
        # - Audio coupling: 1-100uF (mind polarity!)

        # WARNING: Reverse voltage will damage electrolytic capacitors!
        # Use ceramic or film capacitors for AC coupling applications
        """,
        language=F.has_usage_example.Language.ato,
    )

    class Package(StrEnum):
        _01005 = auto()
        _0201 = auto()
        _0402 = auto()
        _0603 = auto()
        _0805 = auto()
        _1206 = auto()
        _1210 = auto()
        _1808 = auto()
        _1812 = auto()
        _1825 = auto()
        _2220 = auto()
        _2225 = auto()
        _3640 = auto()

    package = L.p_field(domain=L.Domains.ENUM(Package))
