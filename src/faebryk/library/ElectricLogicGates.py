# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TypeVar

from faebryk.library.Constant import Constant
from faebryk.library.ElectricLogicGate import ElectricLogicGate
from faebryk.library.Logic import Logic
from faebryk.library.LogicGate import LogicGate

T = TypeVar("T", bound=Logic)


class ElectricLogicGates:
    class OR(ElectricLogicGate):
        def __init__(self, input_cnt: Constant[int]):
            super().__init__(input_cnt, Constant(1), LogicGate.can_logic_or_gate())

    class NOR(ElectricLogicGate):
        def __init__(self, input_cnt: Constant[int]):
            super().__init__(input_cnt, Constant(1), LogicGate.can_logic_nor_gate())

    class NAND(ElectricLogicGate):
        def __init__(self, input_cnt: Constant[int]):
            super().__init__(input_cnt, Constant(1), LogicGate.can_logic_nand_gate())

    class XOR(ElectricLogicGate):
        def __init__(self, input_cnt: Constant[int]):
            super().__init__(input_cnt, Constant(1), LogicGate.can_logic_xor_gate())
