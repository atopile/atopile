# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module, ModuleInterface
from faebryk.library.DifferentialPair import DifferentialPair


class RS485(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            diff_pair = DifferentialPair()

        self.IFs = IFS(self)
