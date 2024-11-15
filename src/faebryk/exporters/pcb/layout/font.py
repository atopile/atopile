# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from rich.progress import track

import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.libs.font import Font
from faebryk.libs.geometry.basic import get_distributed_points_in_polygon

logger = logging.getLogger(__name__)


class FontLayout(Layout):
    def __init__(
        self,
        font: Font,
        font_size: float,
        text: str,
        density: float,
        bbox: tuple[float, float] | None = None,
        scale_to_fit: bool = False,
    ) -> None:
        """
        Create a layout that distributes nodes in a font

        :param font: The font to use
        :param font_size: The font size to use in points
        :param text: The text to distribute
        :param density: The density of the distribution in nodes/point
        :param bbox: The bounding box to distribute the nodes in
        :param scale_to_fit: Whether to scale the font to fit the bounding box
        """
        super().__init__()

        self.font = font

        logger.info(f"Creating font layout for text: {text}")
        polys = font.string_to_polygons(
            text, font_size, bbox=bbox, scale_to_fit=scale_to_fit
        )

        logger.info(f"Finding points in polygons with density: {density}")
        nodes = []
        for p in track(polys, description="Finding points in polygons"):
            nodes.extend(get_distributed_points_in_polygon(polygon=p, density=density))

        logger.info(f"Creating {len(nodes)} nodes in polygons")

        self.coords = [(n.x, n.y) for n in nodes]

    def get_count(self) -> int:
        """
        Get the number of nodes that fit in the font
        """
        return len(self.coords)

    def apply(self, *nodes_to_distribute: Node) -> None:
        """
        Apply the PCB positions to all nodes that are inside the font
        """
        if len(nodes_to_distribute) != len(self.coords):
            logger.warning(
                f"Number of nodes to distribute ({len(nodes_to_distribute)})"
                " does not match"
                f" the number of coordinates ({len(self.coords)})"
            )

        for coord, node in zip(self.coords, nodes_to_distribute):
            node.add(
                F.has_pcb_position_defined_relative_to_parent(
                    (
                        *coord,
                        0,
                        F.has_pcb_position.layer_type.NONE,
                    )
                )
            )

    def __hash__(self) -> int:
        return hash(id(self))
