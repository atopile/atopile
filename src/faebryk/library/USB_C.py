# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class USB_C(fabll.Node):
    usb3 = F.USB3.MakeChild()
    cc1 = F.Electrical.MakeChild()
    cc2 = F.Electrical.MakeChild()
    sbu1 = F.Electrical.MakeChild()
    sbu2 = F.Electrical.MakeChild()
    rx = F.DifferentialPair.MakeChild()
    tx = F.DifferentialPair.MakeChild()

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    net_names = [
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="CC1",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[cc1]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="CC2",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[cc2]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="SBU1",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[sbu1]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="SBU2",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[sbu2]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="RX",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[rx]
        ),
        fabll.Traits.MakeEdge(
            F.has_net_name_suggestion.MakeChild(
                name="TX",
                level=F.has_net_name_suggestion.Level.SUGGESTED
            ),
            owner=[tx]
        ),
    ]

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
            import USB_C, ElectricPower, Resistor

            usb_c = new USB_C

            # Configure differential pair impedances
            usb_c.rx.impedance = 90ohm +/- 10%
            usb_c.tx.impedance = 90ohm +/- 10%
            usb_c.usb3.usb2.dp.impedance = 90ohm +/- 10%
            usb_c.usb3.usb2.dm.impedance = 90ohm +/- 10%

            # Connect power reference for logic levels
            power_3v3 = new ElectricPower
            assert power_3v3.voltage within 3.3V +/- 5%
            usb_c.usb3.usb2.dp.p.reference ~ power_3v3
            usb_c.usb3.usb2.dp.n.reference ~ power_3v3
            usb_c.usb3.usb2.dm.p.reference ~ power_3v3
            usb_c.usb3.usb2.dm.n.reference ~ power_3v3

            # CC resistors for device detection (5.1k for device, 56k for host)
            cc1_resistor = new Resistor
            cc2_resistor = new Resistor
            cc1_resistor.resistance = 5.1kohm +/- 1%  # Device
            cc2_resistor.resistance = 5.1kohm +/- 1%  # Device

            usb_c.cc1 ~> cc1_resistor ~> power_3v3.lv
            usb_c.cc2 ~> cc2_resistor ~> power_3v3.lv

            # Connect to USB controller
            usb_controller.usb_c ~ usb_c
            """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
