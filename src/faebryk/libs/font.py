# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import freetype
from shapely import Point, Polygon

from faebryk.libs.geometry.basic import (
    flatten_polygons,
    transform_polygon,
)

logger = logging.getLogger(__name__)


class Font:
    def __init__(self, ttf: Path):
        super().__init__()

        self.path = ttf

    def string_to_polygons(
        self,
        string: str,
        font_size: float,
        bbox: tuple[float, float] | None = None,
        wrap: bool = False,
        scale_to_fit: bool = False,
    ) -> list[Polygon]:
        """
        Render the polygons of a string from a ttf font file

        :param ttf_path: Path to the ttf font file
        :param string: The string to extract
        :param font_size: The font size in points
        :param bbox: The bounding box to fit the text in, in points
        :param wrap: Wrap the text to fit the bounding box
        :param scale_to_fit: Scale the text to fit the bounding box
        :return: A list of polygons that represent the string
        """

        if wrap and not bbox:
            raise ValueError("Bounding box must be given when wrapping text")

        if scale_to_fit and not bbox:
            raise ValueError("Bounding box must be given when fitting text")

        if wrap and scale_to_fit:
            raise NotImplementedError("Cannot wrap and scale to fit at the same time")

        # TODO: use bezier control points in outline.tags

        face = freetype.Face(str(self.path))
        polygons = []
        offset = Point(0, 0)

        if scale_to_fit:
            font_size = 1

        text_size = Point(0, 0)

        scale = font_size / face.units_per_EM
        for char in string:
            face.load_char(char)

            if bbox and not scale_to_fit:
                if offset.x + face.glyph.advance.x > bbox[0] / scale:
                    if not wrap:
                        break
                    offset = Point(0, offset.y + face.glyph.advance.y)
                    if offset.y > bbox[1] / scale:
                        break

            points = face.glyph.outline.points
            contours = face.glyph.outline.contours

            start = 0

            for contour in contours:
                contour_points = [Point(p) for p in points[start : contour + 1]]
                contour_points.append(contour_points[0])
                start = contour + 1
                contour_points = [
                    Point(p.x + offset.x, p.y + offset.y) for p in contour_points
                ]
                polygons.append(Polygon(contour_points))

            offset = Point(offset.x + face.glyph.advance.x, offset.y)

            if not wrap or not bbox:
                continue

            if offset.x > bbox[0]:
                offset = Point(0, offset.y + face.glyph.advance.y)
                if offset.y > bbox[1]:
                    break

        bounds = [p.bounds for p in polygons]
        min_x, min_y, max_x, max_y = (
            min(b[0] for b in bounds),
            min(b[1] for b in bounds),
            max(b[2] for b in bounds),
            max(b[3] for b in bounds),
        )
        offset = Point(
            -min_x,
            -min_y,
        )

        if scale_to_fit and bbox:
            scale = min(bbox[0] / (max_x - min_x), bbox[1] / (max_y - min_y))

        logger.debug(f"Text size: {text_size}")
        logger.debug(f"Offset: {offset}")
        logger.debug(f"Scale: {scale}")

        polygons = flatten_polygons(polygons)
        polygons = [
            transform_polygon(p, scale=scale, offset=(offset.x, offset.y))
            for p in polygons
        ]

        # Invert the y-axis
        max_y = max(p.bounds[3] for p in polygons)
        polygons = [
            Polygon([(p[0], -p[1] + max_y) for p in polygon.exterior.coords])
            for polygon in polygons
        ]

        return polygons
