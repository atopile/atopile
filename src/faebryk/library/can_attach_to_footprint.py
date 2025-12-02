# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class can_attach_to_footprint(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()
    # Marker trait
    pass
