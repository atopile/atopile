# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class Mechanical(fabll.Node):
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
