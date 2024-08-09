# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.I2C import I2C

logger = logging.getLogger(__name__)


class QWIIC_Connector(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            power = ElectricPower()
            i2c = I2C()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        self.add_trait(has_designator_prefix_defined("J"))
