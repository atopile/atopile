# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class is_surge_protected(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    @abstractmethod
    def get_protection(self) -> F.SurgeProtection: ...
