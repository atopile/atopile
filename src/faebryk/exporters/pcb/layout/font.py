# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Node
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined_relative_to_parent import (
    has_pcb_position_defined_relative_to_parent,
)
from faebryk.libs.font import Font
from faebryk.libs.geometry.basic import fill_poly_with_nodes_on_grid, transform_polygons

logger = logging.getLogger(__name__)


class FontLayout(Layout):
    def __init__(
        self,
        font: Font,
        text: str,
        resolution: tuple[float, float],
        bbox: tuple[float, float] | None = None,
        char_dimensions: tuple[float, float] | None = None,
        kerning: float = 1,
    ) -> None:
        """
        Map a text string with a given font to a grid with a given resolution and map
        a node on each node of the grid that is inside the string.

        :param ttf: Path to the ttf font file
        :param text: Text to render
        :param char_dimensions: Bounding box of a single character (x, y) in mm
        :param resolution: Resolution (x, y) in nodes/mm
        :param kerning: Distance between characters, relative to the resolution of a
        single character in mm
        """
        super().__init__()

        self.font = font

        assert bbox or char_dimensions, "Either bbox or char_dimensions must be given"
        assert len(text) > 0, "Text must not be empty"

        self.poly_glyphs = [
            # poly for letter in text for poly in self.font.letter_to_polygons(letter)
            self.font.letter_to_polygons(letter)
            for letter in text
        ]

        # Debugging
        if logger.isEnabledFor(logging.DEBUG):
           for i, polys in enumerate(self.poly_glyphs):
               logger.debug(f"Found {len(polys)} polygons for letter {text[i]}")
               for p in polys:
                   logger.debug(f"Polygon with {len(p.exterior.coords)} vertices")
                   logger.debug(f"Coords: {list(p.exterior.coords)}")

        char_dim_max = self.font.get_max_glyph_dimensions(text)

        logger.debug(f"Max character dimension in text '{text}': {char_dim_max}")

        offset = (0, 0)
        scale = (1, 1)

        if char_dimensions is None and bbox is not None:
            char_width = (bbox[0] - (len(text) - 1) * kerning) / len(text)
            char_height = bbox[1]

            s = min(
                char_width / (char_dim_max[2] - char_dim_max[0]),
                char_height / (char_dim_max[3] - char_dim_max[1]),
            )
            scale = (s, s)
        else:
            assert char_dimensions is not None
            offset = (-char_dim_max[0], -char_dim_max[1])
            scale = (
                char_dimensions[0] / (char_dim_max[2] - char_dim_max[0]),
                char_dimensions[1] / (char_dim_max[3] - char_dim_max[1]),
            )

        logger.debug(f"Offset: {offset}")
        logger.debug(f"Scale: {scale}")

        self.poly_glyphs = transform_polygons(
            self.poly_glyphs,
            offset,
            scale,
        )

        # set grid offset to half a grid pitch to center the nodes
        grid_offset = (1 / resolution[0] / 2, 1 / resolution[1] / 2)
        grid_pitch = (1 / resolution[0], 1 / resolution[1])

        logger.debug(f"Grid pitch: {grid_pitch}")
        logger.debug(f"Grid offset: {grid_offset}")

        self.coords = []

        for i, polys in enumerate(self.poly_glyphs):
            # Debugging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Processing letter {text[i]}")
                logger.debug(f"Found {len(polys)} polygons for letter {text[i]}")
                for p in polys:
                    logger.debug(f"Polygon with {len(p.exterior.coords)} vertices")
                    logger.debug(f"Coords: {list(p.exterior.coords)}")

            glyph_nodes = fill_poly_with_nodes_on_grid(
                polys=polys,
                grid_pitch=grid_pitch,
                grid_offset=grid_offset,
            )

            # apply character offset in string + kerning
            char_offset_x = (
                max([0] + [c[0] for c in self.coords]) + 1 / resolution[0] + kerning
            )
            for node in glyph_nodes:
                self.coords.append(
                    (
                        node.x + char_offset_x,
                        node.y,
                    )
                )
            logger.debug(f"Found {len(glyph_nodes)} nodes for letter {text[i]}")

        # Move down because the font has the origin in the bottom left while KiCad has
        # it in the top left
        char_offset_y = -max([0] + [c[1] for c in self.coords])
        self.coords = [(c[0], c[1] + char_offset_y) for c in self.coords]

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
            node.add_trait(
                has_pcb_position_defined_relative_to_parent(
                    (
                        coord[0],
                        # TODO mirrored Y-axis bug
                        -coord[1],
                        0,
                        has_pcb_position.layer_type.NONE,
                    )
                )
            )

    def __hash__(self) -> int:
        return hash(id(self))
