# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module, Parameter
from faebryk.core.util import connect_to_all_interfaces
from faebryk.library.Electrical import Electrical
from faebryk.library.Resistor import Resistor
from faebryk.libs.util import times


class Potentiometer(Module):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        self._setup_traits()
        return self

    def __init__(self, resistance: Parameter) -> None:
        super().__init__()
        self._setup_interfaces(resistance)

    def _setup_traits(self):
        ...

    def connect_as_voltage_divider(self, high, low, out):
        self.IFs.resistors[0].connect(high)
        self.IFs.resistors[1].connect(low)
        self.IFs.wiper.connect(out)

    def _setup_interfaces(self, resistance):
        class _IFs(super().IFS()):
            resistors = times(2, Electrical)
            wiper = Electrical()

        class _NODEs(super().NODES()):
            resistors = [Resistor(resistance / 2) for _ in range(2)]

        self.IFs = _IFs(self)
        self.NODEs = _NODEs(self)
        connect_to_all_interfaces(
            self.IFs.wiper,
            [
                self.NODEs.resistors[0].IFs.unnamed[1],
                self.NODEs.resistors[1].IFs.unnamed[1],
            ],
        )
        for i, resistor in enumerate(self.NODEs.resistors):
            self.IFs.resistors[i].connect(resistor.IFs.unnamed[0])
