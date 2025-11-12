# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class Ethernet(fabll.Node):
    """
    1000BASE-T Gigabit Ethernet Interface
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    # Ethernet pairs
    pairs = [F.ElectricSignal.MakeChild() for _ in range(4)]

    # Status LEDs
    led_speed = F.ElectricLogic.MakeChild()  # Speed LED
    led_link = F.ElectricLogic.MakeChild()  # Link LED

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()

    _single_electric_reference = fabll.ChildField(F.has_single_electric_reference)

    # ----------------------------------------
    #                WIP
    # ----------------------------------------

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

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import Ethernet, ElectricPower

        ethernet = new Ethernet

        # Connect power reference for logic levels
        power_3v3 = new ElectricPower
        ethernet.led_speed.reference ~ power_3v3
        ethernet.led_link.reference ~ power_3v3

        # Connect to PHY or connector
        # Four differential pairs for 1000BASE-T
        ethernet_connector.tx_pairs[0] ~ ethernet.pairs[0]
        ethernet_connector.tx_pairs[1] ~ ethernet.pairs[1]
        ethernet_connector.rx_pairs[2] ~ ethernet.pairs[2]
        ethernet_connector.rx_pairs[3] ~ ethernet.pairs[3]

        # Connect status LEDs
        ethernet.led_speed ~ speed_led_output
        ethernet.led_link ~ link_led_output
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()
