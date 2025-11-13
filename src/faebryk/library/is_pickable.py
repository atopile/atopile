# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class is_pickable(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    pass
