# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module, ModuleInterface
from faebryk.library.DifferentialPair import DifferentialPair


class Ethernet(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            tx = DifferentialPair()
            rx = DifferentialPair()

        self.NODEs = _NODEs(self)
