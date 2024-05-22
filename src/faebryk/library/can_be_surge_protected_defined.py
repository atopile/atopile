# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.library.can_be_surge_protected import can_be_surge_protected
from faebryk.library.Electrical import Electrical
from faebryk.library.is_surge_protected import is_surge_protected
from faebryk.library.is_surge_protected_defined import is_surge_protected_defined
from faebryk.library.TVS import TVS

logger = logging.getLogger(__name__)


class can_be_surge_protected_defined(can_be_surge_protected.impl()):
    def __init__(self, low_potential: Electrical, *protect_if: Electrical) -> None:
        super().__init__()
        self.protect_if = protect_if
        self.low_potential = low_potential

    def protect(self):
        obj = self.get_obj()
        tvss = []

        for protect_if in self.protect_if:
            if protect_if.has_trait(can_be_surge_protected):
                tvss.extend(protect_if.get_trait(can_be_surge_protected).protect())
            else:
                tvs = TVS()
                protect_if.NODEs.tvs = tvs
                protect_if.connect_via(tvs, self.low_potential)
                tvss.append(tvs)

        obj.add_trait(is_surge_protected_defined(tvss))
        return tvss

    def is_implemented(self):
        return not self.get_obj().has_trait(is_surge_protected)
