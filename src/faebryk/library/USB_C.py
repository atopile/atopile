# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class USB_C(ModuleInterface):
    usb3: F.USB3
    cc1: F.Electrical
    cc2: F.Electrical
    sbu1: F.Electrical
    sbu2: F.Electrical
    rx: F.DifferentialPair
    tx: F.DifferentialPair

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.cc1.add(F.has_net_name("CC1", level=F.has_net_name.Level.SUGGESTED))
        self.cc2.add(F.has_net_name("CC2", level=F.has_net_name.Level.SUGGESTED))
        self.sbu1.add(F.has_net_name("SBU1", level=F.has_net_name.Level.SUGGESTED))
        self.sbu2.add(F.has_net_name("SBU2", level=F.has_net_name.Level.SUGGESTED))
        self.rx.p.line.add(F.has_net_name("RX", level=F.has_net_name.Level.SUGGESTED))
        self.rx.n.line.add(F.has_net_name("RX", level=F.has_net_name.Level.SUGGESTED))
        self.tx.p.line.add(F.has_net_name("TX", level=F.has_net_name.Level.SUGGESTED))
        self.tx.n.line.add(F.has_net_name("TX", level=F.has_net_name.Level.SUGGESTED))

    usage_example = L.f_field(F.has_usage_example)(
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
    )
