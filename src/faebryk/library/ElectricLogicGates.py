# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.core import Namespace


class ElectricLogicGates(Namespace):
    class OR(F.ElectricLogicGate):
        def __init__(self, input_cnt: int):
            super().__init__(input_cnt, 1, F.LogicGate.can_logic_or_gate())

    class NOR(F.ElectricLogicGate):
        def __init__(self, input_cnt: int):
            super().__init__(input_cnt, 1, F.LogicGate.can_logic_nor_gate())

    class NAND(F.ElectricLogicGate):
        def __init__(self, input_cnt: int):
            super().__init__(input_cnt, 1, F.LogicGate.can_logic_nand_gate())

    class XOR(F.ElectricLogicGate):
        def __init__(self, input_cnt: int):
            super().__init__(input_cnt, 1, F.LogicGate.can_logic_xor_gate())
