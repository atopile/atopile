# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from enum import Enum

from faebryk.core.core import ModuleInterface
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.Range import Range
from faebryk.library.TBD import TBD
from faebryk.libs.units import P, Quantity

logger = logging.getLogger(__name__)


class I2C(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class IFS(ModuleInterface.IFS()):
            scl = ElectricLogic()
            sda = ElectricLogic()

        self.IFs = IFS(self)

        class PARAMS(ModuleInterface.PARAMS()):
            frequency = TBD[Quantity]()

        self.PARAMs = PARAMS(self)

        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))

    def terminate(self):
        # TODO: https://www.ti.com/lit/an/slva689/slva689.pdf

        self.IFs.sda.get_trait(ElectricLogic.can_be_pulled).pull(up=True)
        self.IFs.scl.get_trait(ElectricLogic.can_be_pulled).pull(up=True)

    def _on_connect(self, other: "I2C"):
        super()._on_connect(other)

        self.PARAMs.frequency.merge(other.PARAMs.frequency)

    class SpeedMode(Enum):
        low_speed = 10 * P.khertz
        standard_speed = 100 * P.khertz
        fast_speed = 400 * P.khertz
        high_speed = 3.4 * P.Mhertz

    @staticmethod
    def define_max_frequency_capability(mode: SpeedMode):
        return Range(I2C.SpeedMode.low_speed, mode)
