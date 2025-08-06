# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P
from test.common.resources.fabll_modules.USB2_0_ESD_Protection import (
    USB2_0_ESD_Protection,
)
from test.common.resources.fabll_modules.USB_Type_C_Receptacle_14_pin_Vertical import (
    USB_Type_C_Receptacle_14_pin_Vertical,
)


# TODO bad module
class USB_C_PSU_Vertical(Module):
    # interfaces
    power_out: F.ElectricPower
    usb: F.USB2_0

    # components

    usb_connector: USB_Type_C_Receptacle_14_pin_Vertical  # TODO: make generic
    configuration_resistors = L.list_field(2, F.Resistor)
    gnd_resistor: F.Resistor
    gnd_capacitor: F.Capacitor
    esd: USB2_0_ESD_Protection

    def __preinit__(self):
        self.gnd_capacitor.capacitance.constrain_subset(
            L.Range.from_center_rel(100 * P.nF, 0.05)
        )
        self.gnd_capacitor.max_voltage.constrain_subset(
            L.Range.from_center_rel(16 * P.V, 0.05)
        )
        self.gnd_resistor.resistance.constrain_subset(
            L.Range.from_center_rel(1 * P.Mohm, 0.05)
        )
        for res in self.configuration_resistors:
            res.resistance.constrain_subset(L.Range.from_center_rel(5.1 * P.kohm, 0.05))

        vbus = self.usb_connector.vbus.fused(self)
        vbus_fuse = self.get_first_child_of_type(F.Fuse)
        vbus_fuse.fuse_type.constrain_subset(F.Fuse.FuseType.RESETTABLE)
        vbus_fuse.trip_current.constrain_subset(L.Range.from_center_rel(1 * P.A, 0.05))

        # alliases
        gnd = vbus.lv

        # connect usb and esd
        self.usb_connector.usb.connect_via(self.esd, self.usb)
        vbus.connect(self.power_out)

        # configure as ufp with 5V@max3A
        self.usb_connector.cc1.connect_via(self.configuration_resistors[0], gnd)
        self.usb_connector.cc2.connect_via(self.configuration_resistors[1], gnd)

        # EMI shielding
        self.usb_connector.shield.connect_via(self.gnd_resistor, gnd)
        self.usb_connector.shield.connect_via(self.gnd_capacitor, gnd)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(self.power_out)
