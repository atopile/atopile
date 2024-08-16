# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.core import Module
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.TBD import TBD
from faebryk.libs.units import Quantity


class Battery(Module):
    @classmethod
    def PARAMS(cls):
        class _PARAMs(super().PARAMS()):
            voltage = TBD[Quantity]()
            capacity = TBD[Quantity]()

        return _PARAMs

    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            power = ElectricPower()

        self.IFs = _IFs(self)

        self.PARAMs = self.PARAMS()(self)

        self.IFs.power.PARAMs.voltage.merge(self.PARAMs.voltage)
