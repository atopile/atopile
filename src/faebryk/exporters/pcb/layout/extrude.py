# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.exporters.pcb.layout.layout import Layout
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
    base: F.has_pcb_position.Point = F.has_pcb_position.Point(
        (0, 0, 0, F.has_pcb_position.layer_type.NONE)
    )
    dynamic_rotation: bool = False
    reverse_order: bool = False

    def apply(self, *node: Node):
        """
        Tip: Make sure at least one parent of node has an absolute position defined
        """

        # Remove nodes that have a position defined
        node = tuple(n for n in node if not n.has_trait(F.has_pcb_position))

        vector = self.vector if len(self.vector) == 3 else (*self.vector, 0)

        for i, n in enumerate(
            sorted(
                node,
                key=lambda n: n.get_trait(F.has_designator).get_designator()
                if n.has_trait(F.has_designator)
                else n.get_full_name(),
                reverse=self.reverse_order,
            )
        ):
            vec_i = (
                vector[0] * i,
                vector[1] * i,
                (vector[2] * (i if self.dynamic_rotation else 1)) % 360,
                F.has_pcb_position.layer_type.NONE,
            )
            pos = Geometry.abs_pos(self.base, vec_i)

            n.add(F.has_pcb_position_defined_relative_to_parent(pos))
