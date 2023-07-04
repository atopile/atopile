# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.libs.util import times


class ElectricNAND(Module):
    def __init__(self, input_cnt: int) -> None:
        super().__init__()
        self.input_cnt = input_cnt

        class IFS(Module.IFS()):
            inputs = times(input_cnt, ElectricLogic)
            output = ElectricLogic()

        self.IFs = IFS(self)
