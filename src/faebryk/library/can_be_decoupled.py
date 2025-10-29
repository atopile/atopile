# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


# TODO better name
class can_be_decoupled(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    @abstractmethod
    def decouple(
        self,
        owner: fabll.Node,
        count: int = 1,
    ) -> F.MultiCapacitor: ...
