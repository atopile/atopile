# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.Constant import Constant
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.library.I2C import I2C


class QWIIC(Module):
    """
    Sparkfun QWIIC connection spec. Also compatible with Adafruits STEMMA QT.
    Delivers 3.3V power + I2C over JST SH 1mm pitch 4 pin connectors
    """

    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            i2c = I2C()
            power = ElectricPower()

        self.IFs = _IFs(self)

        # set constraints
        self.IFs.power.PARAMs.voltage.merge(Constant(3.3))
        # TODO: self.IFs.power.PARAMs.source_current.merge(Constant(226 * m))

        self.add_trait(has_designator_prefix_defined("J"))

        self.add_trait(has_datasheet_defined("https://www.sparkfun.com/qwiic"))
