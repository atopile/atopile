# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.has_single_connection import has_single_connection


class has_single_connection_impl(has_single_connection.impl()):
    def get_connection(self):
        conns = self.get_obj().connections
        assert len(conns) == 1
        return conns[0]
