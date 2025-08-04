# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Sequence

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.trait import TraitImpl
from faebryk.libs.library import L
from faebryk.libs.util import times


class LogicGate(Module):
    class can_logic_or_gate(F.LogicOps.can_logic_or.impl()):
        def on_obj_set(self) -> None:
            assert isinstance(self.obj, LogicGate)

        def or_(self, *ins: F.Logic):
            obj = self.obj
            assert isinstance(obj, LogicGate)
            return obj.op(*ins)[0]

    class can_logic_nor_gate(F.LogicOps.can_logic_nor.impl()):
        def on_obj_set(self) -> None:
            assert isinstance(self.obj, LogicGate)

        def nor(self, *ins: F.Logic):
            obj = self.obj
            assert isinstance(obj, LogicGate)
            return obj.op(*ins)[0]

    class can_logic_nand_gate(F.LogicOps.can_logic_nand.impl()):
        def on_obj_set(self) -> None:
            assert isinstance(self.obj, LogicGate)

        def nand(self, *ins: F.Logic):
            obj = self.obj
            assert isinstance(obj, LogicGate)
            return obj.op(*ins)[0]

    class can_logic_xor_gate(F.LogicOps.can_logic_xor.impl()):
        def on_obj_set(self) -> None:
            assert isinstance(self.obj, LogicGate)

        def xor(self, *ins: F.Logic):
            obj = self.obj
            assert isinstance(obj, LogicGate)
            return obj.op(*ins)[0]

    def __init__(
        self,
        input_cnt: int,
        output_cnt: int,
        *functions: TraitImpl,
    ) -> None:
        super().__init__()
        self._input_cnt = input_cnt
        self._output_cnt = output_cnt
        self._functions = list(functions)

    @L.rt_field
    def functions(self):
        return self._functions

    @L.rt_field
    def inputs(self):
        return times(self._input_cnt, F.Logic)

    @L.rt_field
    def outputs(self):
        return times(self._output_cnt, F.Logic)

    @staticmethod
    def op_[T: F.Logic](
        ins1: Sequence[F.Logic], ins2: Sequence[F.Logic], out: Sequence[T]
    ) -> Sequence[T]:
        assert len(ins1) == len(ins2)
        for in_if_mod, in_if in zip(ins1, ins2):
            in_if_mod.connect(in_if)
        return out

    def op(self, *ins: F.Logic):
        return self.op_(ins, self.inputs, self.outputs)
