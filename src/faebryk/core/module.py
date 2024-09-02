# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

from faebryk.core.graphinterface import GraphInterface
from faebryk.core.node import Node
from faebryk.core.trait import Trait
from faebryk.libs.util import unique_ref

logger = logging.getLogger(__name__)


class Module(Node):
    class TraitT(Trait): ...

    specializes: GraphInterface
    specialized: GraphInterface

    def get_most_special(self) -> "Module":
        specialers = {
            specialer
            for specialer_gif in self.specialized.get_direct_connections()
            if (specialer := specialer_gif.node) is not self
            and isinstance(specialer, Module)
        }
        if not specialers:
            return self

        specialest_next = unique_ref(
            specialer.get_most_special() for specialer in specialers
        )

        assert (
            len(specialest_next) == 1
        ), f"Ambiguous specialest {specialest_next} for {self}"
        return next(iter(specialest_next))
