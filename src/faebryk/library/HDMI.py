# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class HDMI(ModuleInterface):
    """
    HDMI interface
    """

    power: F.ElectricPower
    data = L.list_field(3, F.DifferentialPair)
    clock: F.DifferentialPair
    i2c: F.I2C
    cec: F.ElectricLogic
    hotplug: F.ElectricLogic

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    # @staticmethod
    # def define_max_frequency_capability(mode: SpeedMode):
    #     return F.Range(I2C.SpeedMode.low_speed, mode)

    def __preinit__(self) -> None:
        pass
