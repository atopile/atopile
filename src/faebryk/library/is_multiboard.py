# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class is_multiboard(fabll.Node):
    """
    Indicates that the module is a multi-board system parent.

    Attach this trait to a top-level module that contains multiple is_board
    children. Used by the build system to detect system builds and enable
    multi-board features (cross-board DRC, system BOM, 3D viewer).
    """

    is_trait = fabll.Traits.MakeEdge(
        fabll.ImplementsTrait.MakeChild().put_on_type()
    ).put_on_type()
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()
