# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.Range import Range


class Logic(ModuleInterface):
    @staticmethod
    def PARAMS():
        class _PARAMS(ModuleInterface.PARAMS()):
            state = Range(False, True)

        return _PARAMS

    def __init__(self) -> None:
        super().__init__()

        self.PARAMs = self.PARAMS()

    def set(self, on: bool):
        self.PARAMs.state.merge(on)
