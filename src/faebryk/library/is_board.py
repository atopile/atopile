# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class is_board(fabll.Node):
    """
    Indicates that the module is a separate PCB board in a multi-board system.

    Attach this trait to any module that represents a physical circuit board.
    Used by multi-board DRC, system BOM, and 3D viewer features.
    """

    is_trait = fabll.Traits.MakeEdge(
        fabll.ImplementsTrait.MakeChild().put_on_type()
    ).put_on_type()
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()
