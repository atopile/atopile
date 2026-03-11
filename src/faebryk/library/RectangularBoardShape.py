# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class RectangularBoardShape(fabll.Node):
    """
    Basic rectangular board outline.

    The outline is emitted during PCB generation as a synthetic board-only
    footprint whose geometry lives on the Edge.Cuts layer.
    """

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())
    _can_attach_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    x = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    y = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    corner_radius = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)

    @F.implements_design_check.register_post_instantiation_setup_check
    def __check_post_instantiation_setup__(self):
        from faebryk.exporters.pcb.rectangular_board_shape import (
            register_rectangular_board_shape_footprint,
        )

        register_rectangular_board_shape_footprint(self)

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
            import RectangularBoardShape

            board = new RectangularBoardShape
            board.x = 20mm
            board.y = 45mm
            board.corner_radius = 2mm
            """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
