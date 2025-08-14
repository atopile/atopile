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
