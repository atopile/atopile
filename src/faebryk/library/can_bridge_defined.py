# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class can_bridge_defined(fabll.Node):
    def __init__(
        self, in_if: fabll.ModuleInterface, out_if: fabll.ModuleInterface
    ) -> None:
        super().__init__()
        self.get_in = lambda: in_if
        self.get_out = lambda: out_if
