# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module

logger = logging.getLogger(__name__)


class can_be_surge_protected_defined(F.can_be_surge_protected.impl()):
    def __init__(self, low_potential: F.Electrical, *protect_if: F.Electrical) -> None:
        super().__init__()
        self.protect_if = protect_if
        self.low_potential = low_potential

    def protect(self, owner: Module):
        surge_protection = F.SurgeProtection.from_interfaces(
            self.low_potential, *self.protect_if
        )
        owner.add(F.is_surge_protected_defined(surge_protection))
        return surge_protection

    def is_implemented(self):
        return not self.obj.has_trait(F.is_surge_protected)
