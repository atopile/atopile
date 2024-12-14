# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P  # noqa: F401
from faebryk.libs.util import partition

logger = logging.getLogger(__name__)


class SurgeProtection(Module):
    tvs = L.list_f_field(0, F.TVS)()
    nested = L.list_f_field(0, Module)()

    def __init__(self, tvs_count: int = 1):
        super().__init__()
        self._tvs_count = tvs_count

    @classmethod
    def from_interfaces(
        cls, low_potential: F.Electrical, *interfaces_to_protect: F.Electrical
    ):
        to_protect, trait_protectable = partition(
            lambda interface: interface.has_trait(F.can_be_surge_protected),
            interfaces_to_protect,
        )
        to_protect = list(to_protect)
        trait_protectable = list(trait_protectable)
        surge_protection = cls(tvs_count=len(to_protect))

        for interface in trait_protectable:
            nested = interface.get_trait(F.can_be_surge_protected).protect(
                owner=surge_protection
            )
            surge_protection.add(nested, container=surge_protection.nested)

        for interface, tvs in zip(to_protect, surge_protection.tvs):
            interface.connect_via(tvs, low_potential)

        return surge_protection

    def __preinit__(self):
        for _ in range(self._tvs_count):
            self.add_to_container(self._tvs_count, F.TVS, container=self.tvs)
