# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class USB_C_PSU_Vertical(Module):
    # interfaces
    power_out: F.ElectricPower
    usb: F.USB2_0

    # components

    usb_connector: F.USB_Type_C_Receptacle_14_pin_Vertical  # TODO: make generic
    configuration_resistors = L.list_field(2, F.Resistor)
    gnd_resistor: F.Resistor
    gnd_capacitor: F.Capacitor
    esd: F.USB2_0_ESD_Protection
    fuse: F.Fuse

    def __preinit__(self):
        self.gnd_capacitor.capacitance.merge(100 * P.nF)
        self.gnd_capacitor.rated_voltage.merge(16 * P.V)
        self.gnd_resistor.resistance.merge(1 * P.Mohm)
        for res in self.configuration_resistors:
            res.resistance.merge(5.1 * P.kohm)
        self.fuse.fuse_type.merge(F.Fuse.FuseType.RESETTABLE)
        self.fuse.trip_current.merge(F.Range.from_center_rel(1 * P.A, 0.05))

        # alliases
        vcon = self.usb_connector.vbus
        vusb = self.usb.usb_if.buspower
        v5 = self.power_out
        gnd = v5.lv

        vcon.hv.connect_via(self.fuse, v5.hv)
        vcon.lv.connect(gnd)
        vusb.lv.connect(gnd)
        v5.connect(self.esd.usb[0].usb_if.buspower)

        # connect usb data
        self.usb.usb_if.d.connect(
            self.usb_connector.usb.usb_if.d,
            self.esd.usb[0].usb_if.d,
        )

        # configure as ufp with 5V@max3A
        self.usb_connector.cc1.connect_via(self.configuration_resistors[0], gnd)
        self.usb_connector.cc2.connect_via(self.configuration_resistors[1], gnd)

        # EMI shielding
        self.usb_connector.shield.connect_via(self.gnd_resistor, gnd)
        self.usb_connector.shield.connect_via(self.gnd_capacitor, gnd)
