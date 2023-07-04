# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.Logic import Logic
from faebryk.libs.util import times


class NAND(Module):
    def __init__(self, input_cnt: int):
        super().__init__()
        self.input_cnt = input_cnt

        class IFS(Module.IFS()):
            inputs = times(input_cnt, Logic)
            output = Logic()

        self.IFs = IFS(self)

    def nand(self, in1: Logic, in2: Logic):
        self.IFs.inputs[0].connect(in1)
        self.IFs.inputs[1].connect(in2)
        return self.IFs.output
