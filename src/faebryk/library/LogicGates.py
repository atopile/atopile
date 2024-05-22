# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TypeVar

from faebryk.library.Constant import Constant
from faebryk.library.Logic import Logic
from faebryk.library.LogicGate import LogicGate

T = TypeVar("T", bound=Logic)


class LogicGates:
    class OR(LogicGate):
        def __init__(self, input_cnt: Constant[int]):
            super().__init__(input_cnt, Constant(1), LogicGate.can_logic_or_gate())

    class NOR(LogicGate):
        def __init__(self, input_cnt: Constant[int]):
            super().__init__(input_cnt, Constant(1), LogicGate.can_logic_nor_gate())

    class NAND(LogicGate):
        def __init__(self, input_cnt: Constant[int]):
            super().__init__(input_cnt, Constant(1), LogicGate.can_logic_nand_gate())

    class XOR(LogicGate):
        def __init__(self, input_cnt: Constant[int]):
            super().__init__(input_cnt, Constant(1), LogicGate.can_logic_xor_gate())
