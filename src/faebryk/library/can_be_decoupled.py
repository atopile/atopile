# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.trait import Trait

logger = logging.getLogger(__name__)


# TODO better name
class can_be_decoupled(Trait):
    @abstractmethod
    def decouple(
        self,
        owner: fabll.Node,
        count: int = 1,
    ) -> F.MultiCapacitor: ...
