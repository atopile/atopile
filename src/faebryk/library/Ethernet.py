# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L

logger = logging.getLogger(__name__)

class Ethernet(ModuleInterface):
    tx: F.DifferentialPair
    rx: F.DifferentialPair

class GigabitEthernet(ModuleInterface):
    """
    1000BASE-T Gigabit Ethernet Interface
    """
    # Ethernet pairs
    pair0: F.DifferentialPair  # Ethernet_Pair0_P/N
    pair1: F.DifferentialPair  # Ethernet_Pair1_P/N
    pair2: F.DifferentialPair  # Ethernet_Pair2_P/N
    pair3: F.DifferentialPair  # Ethernet_Pair3_P/N

    # Status LEDs
    led_speed: F.ElectricLogic  # Speed LED
    led_link: F.ElectricLogic     # Link LED


    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __preinit__(self) -> None:
        pass
