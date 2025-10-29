# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class is_surge_protected_defined(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(self, protection: F.SurgeProtection) -> None:
        super().__init__()
        self.protection = protection

    def get_protection(self):
        return self.protection
