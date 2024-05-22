# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from enum import IntEnum

from faebryk.core.core import ModuleInterface
from faebryk.library.ElectricLogic import ElectricLogic, can_be_pulled
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.Range import Range
from faebryk.library.TBD import TBD
from faebryk.libs.units import M, k

logger = logging.getLogger(__name__)


class I2C(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class IFS(ModuleInterface.IFS()):
            scl = ElectricLogic()
            sda = ElectricLogic()

        self.IFs = IFS(self)

        class PARAMS(ModuleInterface.PARAMS()):
            frequency = TBD()

        self.PARAMs = PARAMS(self)

        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))

    def terminate(self):
        # TODO: https://www.ti.com/lit/an/slva689/slva689.pdf

        self.IFs.sda.get_trait(can_be_pulled).pull(up=True)
        self.IFs.scl.get_trait(can_be_pulled).pull(up=True)

    def _on_connect(self, other: "I2C"):
        super()._on_connect(other)

        self.PARAMs.frequency.merge(other.PARAMs.frequency)

    class SpeedMode(IntEnum):
        low_speed = 10 * k
        standard_speed = 100 * k
        fast_speed = 400 * k
        high_speed = 3.4 * M

    @staticmethod
    def define_max_frequency_capability(mode: SpeedMode):
        return Range(I2C.SpeedMode.low_speed, mode)
