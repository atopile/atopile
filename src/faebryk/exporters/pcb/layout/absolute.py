# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.exporters.pcb.layout.layout import Layout

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=True)
class LayoutAbsolute(Layout):
    pos: F.has_pcb_position.Point

    def apply(self, *node: Node):
        """
        Tip: Make sure at least one parent of node has an absolute position defined
        """
        # Remove nodes that have a position defined
        node = tuple(n for n in node if not n.has_trait(F.has_pcb_position))

        for n in node:
            n.add(F.has_pcb_position_defined_relative_to_parent(self.pos))
