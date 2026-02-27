# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class MDIO(fabll.Node):
    """
    Management Data Input/Output (MDIO) interface
    IEEE 802.3 clause 22/45 serial management interface (SMI)
    for configuring and monitoring Ethernet PHYs.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    mdc = F.ElectricLogic.MakeChild()  # Management Data Clock
    mdio = F.ElectricLogic.MakeChild()  # Management Data I/O (bidirectional)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    _single_electric_reference = fabll.Traits.MakeEdge(
        F.has_single_electric_reference.MakeChild()
    )

    net_names = [
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="MDC", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[mdc],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="MDIO", level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[mdio],
        ),
    ]

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        import MDIO, ElectricPower

        mdio_bus = new MDIO

        # Connect power reference for logic levels
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        mdio_bus.mdc.reference ~ power_3v3
        mdio_bus.mdio.reference ~ power_3v3

        # Connect between MAC (MCU) and PHY
        microcontroller.mdio ~ mdio_bus
        ethernet_phy.mdio ~ mdio_bus
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
