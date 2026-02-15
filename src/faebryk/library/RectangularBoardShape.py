# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING

import faebryk.core.node as fabll
import faebryk.library._F as F

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer


class RectangularBoardShape(fabll.Node):
    """
    Parameterized rectangular PCB outline.

    This module defines a rectangular board shape in the PCB export pipeline.
    The outline is generated as a dedicated footprint on the Edge.Cuts layer from:
    - width
    - height
    - corner_radius
    - mounting_hole_diameter (optional; creates 4 corner holes)
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())
    _can_attach_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )
    _implements_board_shape = fabll.Traits.MakeEdge(
        F.implements_board_shape.MakeChild()
    )

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

    def __apply_board_shape__(self, transformer: "PCB_Transformer") -> None:
        from faebryk.exporters.pcb.board_shape.rectangular_board_shape import (
            apply_rectangular_board_shape,
        )

        apply_rectangular_board_shape(transformer, shape=self)
