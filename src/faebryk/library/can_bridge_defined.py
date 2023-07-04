# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.can_bridge import can_bridge


class can_bridge_defined(can_bridge.impl()):
    def __init__(self, in_if: ModuleInterface, out_if: ModuleInterface) -> None:
        super().__init__()
        self.get_in = lambda: in_if
        self.get_out = lambda: out_if
