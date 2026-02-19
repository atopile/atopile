# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class is_cable(fabll.Node):
    """
    Indicates that the module is a cable or wire interconnect between boards.

    Cables are excluded from PCB layout and represent legitimate cross-board
    electrical paths. The cross-board DRC uses this trait to distinguish
    intended inter-board connections from wiring errors.
    """

    is_trait = fabll.Traits.MakeEdge(
        fabll.ImplementsTrait.MakeChild().put_on_type()
    ).put_on_type()
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()
