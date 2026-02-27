# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class RMII(fabll.Node):
    """
    Reduced Media Independent Interface (RMII)
    IEEE 802.3u compliant 10/100 Mbps interface between MAC and PHY.
    Uses a 50 MHz reference clock and 2-bit data paths.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    # Clock signal - 50 MHz reference
    ref_clk = F.ElectricLogic.MakeChild()

    # Transmit signals
    txd = [F.ElectricLogic.MakeChild() for _ in range(2)]  # TXD[1:0]
    tx_en = F.ElectricLogic.MakeChild()  # TX_EN

    # Receive signals
    rxd = [F.ElectricLogic.MakeChild() for _ in range(2)]  # RXD[1:0]
    crs_dv = F.ElectricLogic.MakeChild()  # CRS_DV
    rx_er = F.ElectricLogic.MakeChild()  # RX_ER (optional)

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
                name="RMII_REF_CLK",
                level=F.has_net_name_suggestion.Level.SUGGESTED,
            ),
            owner=[ref_clk],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="RMII_TX_EN",
                level=F.has_net_name_suggestion.Level.SUGGESTED,
            ),
            owner=[tx_en],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="RMII_CRS_DV",
                level=F.has_net_name_suggestion.Level.SUGGESTED,
            ),
            owner=[crs_dv],
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="RMII_RX_ER",
                level=F.has_net_name_suggestion.Level.SUGGESTED,
            ),
            owner=[rx_er],
        ),
    ]

    for i, txd_signal in enumerate(txd):
        txd_signal.add_dependant(
            fabll.Traits.MakeEdge(
                F.has_net_name_suggestion.MakeChild(
                    name=f"RMII_TXD{i}",
                    level=F.has_net_name_suggestion.Level.SUGGESTED,
                ),
                owner=[txd_signal],
            )
        )

    for i, rxd_signal in enumerate(rxd):
        rxd_signal.add_dependant(
            fabll.Traits.MakeEdge(
                F.has_net_name_suggestion.MakeChild(
                    name=f"RMII_RXD{i}",
                    level=F.has_net_name_suggestion.Level.SUGGESTED,
                ),
                owner=[rxd_signal],
            )
        )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        import RMII, ElectricPower

        rmii = new RMII

        # Connect power reference for logic levels
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%

        # Connect between MAC (MCU) and PHY
        microcontroller.rmii ~ rmii
        ethernet_phy.rmii ~ rmii
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
