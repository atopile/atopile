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

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Ethernet, ElectricPower, Electrical

        module UsageExample:
            ethernet = new Ethernet

            pair_0_p = new Electrical
            pair_0_n = new Electrical
            pair_1_p = new Electrical
            pair_1_n = new Electrical
            led_anode = new Electrical
            power_3v3 = new ElectricPower
            assert power_3v3.voltage within 3.3V +/- 5%

            ethernet.pairs[0].p.line ~ pair_0_p
            ethernet.pairs[0].n.line ~ pair_0_n
            ethernet.led_speed.line ~ power_3v3.hv
            ethernet.led_speed.reference.lv ~ power_3v3.lv
            ethernet.led_link.line ~ led_anode
            ethernet.led_link.reference.lv ~ power_3v3.lv
            ethernet.pairs[1].n.line ~ pair_1_n
            ethernet.pairs[1].p.line ~ pair_1_p

            # or
            ethernet2 = new Ethernet
            ethernet2 ~ ethernet
        """,
        language=F.has_usage_example.Language.ato,
    )
