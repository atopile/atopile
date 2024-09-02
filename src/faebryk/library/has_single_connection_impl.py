# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_single_connection_impl(F.has_single_connection.impl()):
    def get_connection(self):
        conns = self.obj.connections
        assert len(conns) == 1
        return conns[0]
