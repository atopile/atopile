# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class Ethernet(ModuleInterface):
    """
    1000BASE-T Gigabit Ethernet Interface
    """

    # Ethernet pairs
    pairs = L.list_field(4, F.DifferentialPair)

    # Status LEDs
    led_speed: F.ElectricLogic  # Speed LED
    led_link: F.ElectricLogic  # Link LED

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.led_speed.line.add(
            F.has_net_name("ETH_LED_SPEED", level=F.has_net_name.Level.SUGGESTED)
        )
        self.led_link.line.add(
            F.has_net_name("ETH_LED_LINK", level=F.has_net_name.Level.SUGGESTED)
        )
        for i, pair in enumerate(self.pairs):
            pair.p.line.add(
                F.has_net_name(f"ETH_P{i}", level=F.has_net_name.Level.SUGGESTED)
            )
            pair.n.line.add(
                F.has_net_name(f"ETH_P{i}", level=F.has_net_name.Level.SUGGESTED)
            )
