# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.library._F as F
from faebryk.core.core import Namespace
from faebryk.core.trait import Trait


class LogicOps(Namespace):
    class can_logic(Trait):
        @abstractmethod
        def op(self, *ins: F.Logic) -> F.Logic: ...

    class can_logic_or(can_logic):
        @abstractmethod
        def or_(self, *ins: F.Logic) -> F.Logic: ...

        def op(self, *ins: F.Logic) -> F.Logic:
            return self.or_(*ins)

    class can_logic_and(can_logic):
        @abstractmethod
        def and_(self, *ins: F.Logic) -> F.Logic: ...

        def op(self, *ins: F.Logic) -> F.Logic:
            return self.and_(*ins)

    class can_logic_nor(can_logic):
        @abstractmethod
        def nor(self, *ins: F.Logic) -> F.Logic: ...

        def op(self, *ins: F.Logic) -> F.Logic:
            return self.nor(*ins)

    class can_logic_nand(can_logic):
        @abstractmethod
        def nand(self, *ins: F.Logic) -> F.Logic: ...

        def op(self, *ins: F.Logic) -> F.Logic:
            return self.nand(*ins)

    class can_logic_xor(can_logic):
        @abstractmethod
        def xor(self, *ins: F.Logic) -> F.Logic: ...

        def op(self, *ins: F.Logic) -> F.Logic:
            return self.xor(*ins)
