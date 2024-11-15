# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.exporters.pcb.layout.heuristic_decoupling import Params, place_next_to
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=True)
class LayoutNextToPin(Layout):
    interface: F.Electrical
    distance_between_pad_edges: float = 1
    extra_rotation_of_footprint: float = 0

    def apply(self, *node: Node):
        """
        Tip: Make sure at least one parent of node has an absolute position defined
        """
        # Remove nodes that have a position defined
        node = tuple(n for n in node if not n.has_trait(F.has_pcb_position))

        for n in node:
            assert isinstance(n, Module)
            electrical = not_none(self.interface)
            logger.debug(f"Placing {n} next to {electrical}")
            place_next_to(
                electrical,
                n,
                route=True,
                params=Params(
                    self.distance_between_pad_edges, self.extra_rotation_of_footprint
                ),
            )
