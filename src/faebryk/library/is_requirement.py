# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import faebryk.core.node as fabll


class is_requirement(fabll.Node):
    """Trait marking a node as a simulation requirement.

    Added to Requirement nodes for uniform discovery.
    Enables the two-phase architecture: run simulations first,
    then verify requirements against cached data.
    """

    is_trait = fabll.Traits.MakeEdge(
        fabll.ImplementsTrait.MakeChild().put_on_type()
    ).put_on_type()
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()
