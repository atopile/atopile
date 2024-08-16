# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.Resistor import Resistor
from faebryk.library.TBD import TBD
from faebryk.libs.units import Quantity
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class Resistor_Voltage_Divider(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            resistor = times(2, Resistor)

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            node = times(3, Electrical)

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            ratio = TBD[Quantity]()
            max_current = TBD[Quantity]()

        self.PARAMs = _PARAMs(self)

        self.IFs.node[0].connect_via(self.NODEs.resistor[0], self.IFs.node[1])
        self.IFs.node[1].connect_via(self.NODEs.resistor[1], self.IFs.node[2])

        self.add_trait(can_bridge_defined(self.IFs.node[0], self.IFs.node[1]))
