# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.Electrical import Electrical
from faebryk.library.Resistor import Resistor
from faebryk.library.TBD import TBD
from faebryk.libs.units import Quantity
from faebryk.libs.util import times


class Potentiometer(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            resistors = times(2, Electrical)
            wiper = Electrical()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            total_resistance = TBD[Quantity]()

        self.PARAMs = _PARAMs(self)

        class _NODEs(Module.NODES()):
            resistors = times(2, Resistor)

        self.NODEs = _NODEs(self)

        for i, resistor in enumerate(self.NODEs.resistors):
            self.IFs.resistors[i].connect_via(resistor, self.IFs.wiper)

            # TODO use range(0, total_resistance)
            resistor.PARAMs.resistance.merge(self.PARAMs.total_resistance)

    def connect_as_voltage_divider(
        self, high: Electrical, low: Electrical, out: Electrical
    ):
        self.IFs.resistors[0].connect(high)
        self.IFs.resistors[1].connect(low)
        self.IFs.wiper.connect(out)
