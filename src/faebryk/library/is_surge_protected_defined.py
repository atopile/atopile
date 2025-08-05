# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F

logger = logging.getLogger(__name__)


class is_surge_protected_defined(F.is_surge_protected.impl()):
    def __init__(self, protection: F.SurgeProtection) -> None:
        super().__init__()
        self.protection = protection

    def get_protection(self):
        return self.protection
