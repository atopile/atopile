# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.core import Namespace


class LogicGates(Namespace):
    class OR(F.LogicGate):
        def __init__(self, input_cnt: int):
            super().__init__(input_cnt, 1, F.LogicGate.can_logic_or_gate())

    class NOR(F.LogicGate):
        def __init__(self, input_cnt: int):
            super().__init__(input_cnt, 1, F.LogicGate.can_logic_nor_gate())

    class NAND(F.LogicGate):
        def __init__(self, input_cnt: int):
            super().__init__(input_cnt, 1, F.LogicGate.can_logic_nand_gate())

    class XOR(F.LogicGate):
        def __init__(self, input_cnt: int):
            super().__init__(input_cnt, 1, F.LogicGate.can_logic_xor_gate())
