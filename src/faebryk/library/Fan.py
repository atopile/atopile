# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.ElectricPower import ElectricPower


class Fan(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            power = ElectricPower()

        self.IFs = _IFs(self)

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)
