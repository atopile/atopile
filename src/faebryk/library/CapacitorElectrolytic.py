# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class CapacitorElectrolytic(F.Capacitor):
    pickable = None  # type: ignore
    can_attach_to_footprint_symmetrically = None  # type: ignore

    anode: F.Electrical
    cathode: F.Electrical

    def __preinit__(self):
        self.power.hv.connect(self.anode)
        self.power.lv.connect(self.cathode)

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.anode, self.cathode)

    @L.rt_field
    def has_pin_association_heuristic_lookup_table(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power.hv: ["anode", "a"],
                self.power.lv: ["cathode", "c"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.anode.add(F.has_net_name("anode", level=F.has_net_name.Level.SUGGESTED))
        self.cathode.add(
            F.has_net_name("cathode", level=F.has_net_name.Level.SUGGESTED)
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
