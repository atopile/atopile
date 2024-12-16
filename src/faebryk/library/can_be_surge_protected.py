# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING

from faebryk.core.module import Module
from faebryk.core.trait import Trait

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from faebryk.library.SurgeProtection import SurgeProtection


class can_be_surge_protected(Trait):
    @abstractmethod
    def protect(self, owner: Module) -> "SurgeProtection": ...
