# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F


class has_single_connection_impl(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def get_connection(self):
        conns = self.obj.connections
        assert len(conns) == 1
        return conns[0]
