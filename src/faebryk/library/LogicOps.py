# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import TypeVar

from faebryk.core.core import NodeTrait
from faebryk.library.Logic import Logic

T = TypeVar("T", bound=Logic)


class LogicOps:
    class can_logic(NodeTrait):
        @abstractmethod
        def op(self, *ins: Logic) -> Logic: ...

    class can_logic_or(can_logic):
        @abstractmethod
        def or_(self, *ins: Logic) -> Logic: ...

        def op(self, *ins: Logic) -> Logic:
            return self.or_(*ins)

    class can_logic_and(can_logic):
        @abstractmethod
        def and_(self, *ins: Logic) -> Logic: ...

        def op(self, *ins: Logic) -> Logic:
            return self.and_(*ins)

    class can_logic_nor(can_logic):
        @abstractmethod
        def nor(self, *ins: Logic) -> Logic: ...

        def op(self, *ins: Logic) -> Logic:
            return self.nor(*ins)

    class can_logic_nand(can_logic):
        @abstractmethod
        def nand(self, *ins: Logic) -> Logic: ...

        def op(self, *ins: Logic) -> Logic:
            return self.nand(*ins)

    class can_logic_xor(can_logic):
        @abstractmethod
        def xor(self, *ins: Logic) -> Logic: ...

        def op(self, *ins: Logic) -> Logic:
            return self.xor(*ins)
