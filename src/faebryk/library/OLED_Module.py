# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

from faebryk.core.core import Module
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.I2C import I2C
from faebryk.library.Range import Range
from faebryk.library.TBD import TBD

logger = logging.getLogger(__name__)


class OLED_Module(Module):
    class Resolution(Enum):
        H64xV32 = auto()
        H128xV32 = auto()
        H128xV64 = auto()
        H256xV64 = auto()

    class DisplayController(Enum):
        SSD1315 = auto()
        SSD1306 = auto()

    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            power = ElectricPower()
            i2c = I2C()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            resolution = TBD[self.Resolution]()
            display_controller = TBD[self.DisplayController]()

        self.PARAMs = _PARAMs(self)

        self.IFs.power.PARAMs.voltage.merge(Range(3.0, 5))

        self.IFs.power.get_trait(can_be_decoupled).decouple()

        self.add_trait(has_designator_prefix_defined("OLED"))
