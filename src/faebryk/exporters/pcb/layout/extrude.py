# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

from faebryk.core.core import (
    Node,
)
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined_relative_to_parent import (
    has_pcb_position_defined_relative_to_parent,
)
from faebryk.libs.geometry.basic import Geometry

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=True)
class LayoutExtrude(Layout):
    vector: tuple[float, float] | tuple[float, float, float]
    base: has_pcb_position.Point = has_pcb_position.Point(
        (0, 0, 0, has_pcb_position.layer_type.NONE)
    )

    def apply(self, *node: Node):
        """
        Tip: Make sure at least one parent of node has an absolute position defined
        """

        # Remove nodes that have a position defined
        node = tuple(n for n in node if not n.has_trait(has_pcb_position))

        vector = self.vector if len(self.vector) == 3 else (*self.vector, 0)

        for i, n in enumerate(node):
            vec_i = (
                vector[0] * i,
                vector[1] * i,
                vector[2],
                has_pcb_position.layer_type.NONE,
            )
            pos = Geometry.abs_pos(self.base, vec_i)

            n.add_trait(has_pcb_position_defined_relative_to_parent(pos))
