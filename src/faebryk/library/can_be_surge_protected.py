# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING

import faebryk.core.node as fabll

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from faebryk.library.SurgeProtection import SurgeProtection


class can_be_surge_protected(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    @abstractmethod
    def protect(self, owner: fabll.Node) -> "SurgeProtection": ...
