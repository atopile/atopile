# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from enum import Enum

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import cast_assert

logger = logging.getLogger(__name__)


class I2C(ModuleInterface):
    scl: F.ElectricLogic
    sda: F.ElectricLogic

    frequency: F.TBD

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def terminate(self):
        # TODO: https://www.ti.com/lit/an/slva689/slva689.pdf

        self.sda.pulled.pull(up=True)
        self.scl.pulled.pull(up=True)

    class SpeedMode(Enum):
        low_speed = 10 * P.khertz
        standard_speed = 100 * P.khertz
        fast_speed = 400 * P.khertz
        high_speed = 3.4 * P.Mhertz

    @staticmethod
    def define_max_frequency_capability(mode: SpeedMode):
        return F.Range(I2C.SpeedMode.low_speed, mode)

    def __preinit__(self) -> None:
        self.frequency.add(
            F.is_dynamic_by_connections(lambda mif: cast_assert(I2C, mif).frequency)
        )
