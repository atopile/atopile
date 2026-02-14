# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class RectangularBoardShape(fabll.Node):
    """
    Parameterized rectangular PCB outline.

    This module defines a rectangular board shape in the PCB export pipeline.
    The outline is generated directly on the Edge.Cuts layer from:
    - width
    - height
    - corner_radius
    - mounting_hole_diameter (optional; creates 4 corner holes)
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    width = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    height = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    corner_radius = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    mounting_hole_diameter = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
            import RectangularBoardShape

            board = new RectangularBoardShape
            board.width = 20mm
            board.height = 30mm
            board.corner_radius = 3mm
            board.mounting_hole_diameter = 3.3mm
            """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
