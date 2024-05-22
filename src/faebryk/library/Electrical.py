# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.TBD import TBD


class Electrical(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class PARAMS(ModuleInterface.PARAMS()):
            potential = TBD()

        self.PARAMs = PARAMS(self)
