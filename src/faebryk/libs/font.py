# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from math import inf
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from shapely import Polygon

logger = logging.getLogger(__name__)


class Font:
    def __init__(self, ttf: Path):
        super().__init__()

        self.path = ttf
        self.font = TTFont(ttf)

    def get_max_glyph_dimensions(
        self, text: str | None = None
    ) -> tuple[float, float, float, float]:
        """
        Get the maximum dimensions of all glyphs combined in a font
        """
        glyphset = self.font.getGlyphSet()
        bp = BoundsPen(glyphset)

        max_dim = (inf, inf, -inf, -inf)
        for glyph_name in glyphset.keys() if text is None else set(text):
            glyphset[glyph_name].draw(bp)

            if not bp.bounds:
                continue

            max_dim = (
                min(max_dim[0], bp.bounds[0]),
                min(max_dim[1], bp.bounds[1]),
                max(max_dim[2], bp.bounds[2]),
                max(max_dim[3], bp.bounds[3]),
            )

        return max_dim

    def letter_to_polygons(self, letter: str) -> list[Polygon]:
        """
        Extract the polygons of a single letter from a ttf font file

        :param ttf_path: Path to the ttf font file
        :param letter: The letter to extract
        :return: A list of polygons that represent the letter
        """
        font = self.font
        cmap = font.getBestCmap()
        glyph_set = font.getGlyphSet()
        glyph = glyph_set[cmap[ord(letter)]]
        contours = Font.extract_contours(glyph)

        polys = []
        for contour in contours:
            polys.append(Polygon(contour))

        return polys

    @staticmethod
    def extract_contours(glyph) -> list[list[tuple[float, float]]]:
        """
        Extract the contours of a glyph

        :param glyph: The glyph to extract the contours from
        :return: A list of contours, each represented by a list of coordinates
        """
        contours = []
        current_contour = []
        pen = RecordingPen()
        glyph.draw(pen)
        trace = pen.value
        for flag, coords in trace:
            if flag == "lineTo":  # On-curve point
                current_contour.append(coords[0])
            if flag == "moveTo":  # Move to a new contour
                current_contour = [coords[0]]
            if flag == "closePath":  # Close the current contour
                current_contour.append(current_contour[0])
                contours.append(current_contour)
        return contours
