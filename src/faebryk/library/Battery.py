# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.core import Module, Parameter
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.TBD import TBD


class Battery(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            power = ElectricPower()

        self.IFs = _IFs(self)

        class _PARAMS(Module.PARAMS()):
            voltage: Parameter = TBD()

        self.PARAMs = _PARAMS(self)

        self.IFs.power.PARAMs.voltage.merge(self.PARAMs.voltage)
