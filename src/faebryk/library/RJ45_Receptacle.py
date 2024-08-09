# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

from faebryk.core.core import Module
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.TBD import TBD
from faebryk.libs.util import times


class RJ45_Receptacle(Module):
    class Mounting(Enum):
        TH = auto()
        SMD = auto()

    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            pin = times(8, Electrical)
            shield = Electrical()

        self.IFs = _IFs(self)

        self.add_trait(has_designator_prefix_defined("J"))

        class _PARAMS(super().PARAMS()):
            mounting = TBD[self.Mounting]()

        self.PARAMs = _PARAMS(self)
