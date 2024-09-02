# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F

logger = logging.getLogger(__name__)


class can_be_surge_protected_defined(F.can_be_surge_protected.impl()):
    def __init__(self, low_potential: F.Electrical, *protect_if: F.Electrical) -> None:
        super().__init__()
        self.protect_if = protect_if
        self.low_potential = low_potential

    def protect(self):
        obj = self.obj
        tvss = []

        for protect_if in self.protect_if:
            if protect_if.has_trait(F.can_be_surge_protected):
                tvss.extend(protect_if.get_trait(F.can_be_surge_protected).protect())
            else:
                tvs = protect_if.add(F.TVS(), "tvs")
                protect_if.connect_via(tvs, self.low_potential)
                tvss.append(tvs)

        obj.add_trait(F.is_surge_protected_defined(tvss))
        return tvss

    def is_implemented(self):
        return not self.obj.has_trait(F.is_surge_protected)
