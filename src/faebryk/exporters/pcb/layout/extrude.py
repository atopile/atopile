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
    """
    Extrude nodes in a direction from a base position.

    :param vector: x (spacing), y (spacing), r (rotation of the node).
    :param base: The base position to extrude from.
    x (start), y (start), r (direction of extrusion), pcb layer.
    :param dynamic_rotation: If True, the rotation will be multiplied by the index
    of the node, resulting in each consecutive node being rotated more.
    """

    vector: tuple[float, float] | tuple[float, float, float]
    base: has_pcb_position.Point = has_pcb_position.Point(
        (0, 0, 0, has_pcb_position.layer_type.NONE)
    )
    dynamic_rotation: bool = False

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
                (vector[2] * (i if self.dynamic_rotation else 1)) % 360,
                has_pcb_position.layer_type.NONE,
            )
            pos = Geometry.abs_pos(self.base, vec_i)

            n.add_trait(has_pcb_position_defined_relative_to_parent(pos))
