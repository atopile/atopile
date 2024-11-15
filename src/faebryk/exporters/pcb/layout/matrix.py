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
class LayoutMatrix(Layout):
    """
    Distribute nodes in a matrix.

    :param vector:x (spacing), y (spacing), r (rotation of the node).
    :param distribution: x (number of rows), y (number of columns).
    :param base: The base position to extrude from.
    x (start), y (start), r (direction of extrusion), pcb layer.
    """

    vector: tuple[float, float] | tuple[float, float, float]
    distribution: tuple[int, int]
    base: F.has_pcb_position.Point = F.has_pcb_position.Point(
        (0, 0, 0, F.has_pcb_position.layer_type.NONE)
    )

    def apply(self, *node: Node):
        """
        Tip: Make sure at least one parent of node has an absolute position defined
        """

        # Remove nodes that have a position defined
        node = tuple(n for n in node if not n.has_trait(F.has_pcb_position))

        vector = self.vector if len(self.vector) == 3 else (*self.vector, 0)

        number_of_nodes = len(node)
        number_of_distributions = self.distribution[0] * self.distribution[1]

        if number_of_nodes > number_of_distributions:
            raise ValueError(
                f"Number of nodes ({number_of_nodes}) is more than we can distribute ({number_of_distributions})"  # noqa E501
            )
        node_index = 0
        for x in range(self.distribution[0]):
            for y in range(self.distribution[1]):
                if node_index >= number_of_nodes:
                    logger.debug(
                        f"No more nodes ({number_of_nodes}) to distribute ({number_of_distributions})"  # noqa E501
                    )
                    return
                vec_i = (
                    vector[0] * x,
                    vector[1] * y,
                    vector[2],
                    F.has_pcb_position.layer_type.NONE,
                )
                pos = Geometry.abs_pos(self.base, vec_i)

                node[node_index].add(F.has_pcb_position_defined_relative_to_parent(pos))
                node_index += 1
