# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class CapacitorElectrolytic(F.Capacitor):
    pickable = None
    attach_to_footprint = None

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
