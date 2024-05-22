# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Sequence, TypeVar

from faebryk.core.core import Module, TraitImpl
from faebryk.library.Constant import Constant
from faebryk.library.Logic import Logic
from faebryk.library.LogicOps import LogicOps
from faebryk.libs.util import times

T = TypeVar("T", bound=Logic)


class LogicGate(Module):
    class can_logic_or_gate(LogicOps.can_logic_or.impl()):
        def on_obj_set(self) -> None:
            assert isinstance(self.get_obj(), LogicGate)

        def or_(self, *ins: Logic):
            obj = self.get_obj()
            assert isinstance(obj, LogicGate)
            return obj.op(*ins)[0]

    class can_logic_nor_gate(LogicOps.can_logic_nor.impl()):
        def on_obj_set(self) -> None:
            assert isinstance(self.get_obj(), LogicGate)

        def nor(self, *ins: Logic):
            obj = self.get_obj()
            assert isinstance(obj, LogicGate)
            return obj.op(*ins)[0]

    class can_logic_nand_gate(LogicOps.can_logic_nand.impl()):
        def on_obj_set(self) -> None:
            assert isinstance(self.get_obj(), LogicGate)

        def nand(self, *ins: Logic):
            obj = self.get_obj()
            assert isinstance(obj, LogicGate)
            return obj.op(*ins)[0]

    class can_logic_xor_gate(LogicOps.can_logic_xor.impl()):
        def on_obj_set(self) -> None:
            assert isinstance(self.get_obj(), LogicGate)

        def xor(self, *ins: Logic):
            obj = self.get_obj()
            assert isinstance(obj, LogicGate)
            return obj.op(*ins)[0]

    def __init__(
        self,
        input_cnt: Constant[int],
        output_cnt: Constant[int],
        *functions: TraitImpl,
    ) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            inputs = times(input_cnt, Logic)
            outputs = times(output_cnt, Logic)

        self.IFs = IFS(self)

        for f in functions:
            self.add_trait(f)

    @staticmethod
    def op_(
        ins1: Sequence[Logic], ins2: Sequence[Logic], out: Sequence[T]
    ) -> Sequence[T]:
        assert len(ins1) == len(ins2)
        for in_if_mod, in_if in zip(ins1, ins2):
            in_if_mod.connect(in_if)
        return out

    def op(self, *ins: Logic):
        return self.op_(ins, self.IFs.inputs, self.IFs.outputs)
