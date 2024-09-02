# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface


class can_bridge_defined(F.can_bridge.impl()):
    def __init__(self, in_if: ModuleInterface, out_if: ModuleInterface) -> None:
        super().__init__()
        self.get_in = lambda: in_if
        self.get_out = lambda: out_if
