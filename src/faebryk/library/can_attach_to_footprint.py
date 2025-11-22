# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.core.node as fabll
import faebryk.library._F as F


class can_attach_to_footprint(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()
    # Marker trait
    pass
