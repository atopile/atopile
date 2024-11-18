# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class USB_C_PowerOnly(ModuleInterface):
    power: F.ElectricPower
    cc1: F.Electrical
    cc2: F.Electrical

    @L.rt_field
    def surge_protected(self):
        return F.can_be_surge_protected_defined(
            self.power.lv,
            self.power.hv,
            self.cc1,
            self.cc2,
        )

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def connect_to_full_usb_c(self, usb_c: F.USB_C):
        self.power.connect(usb_c.usb3.usb3_if.usb_if.buspower)
        self.cc1.connect(usb_c.cc1)
        self.cc2.connect(usb_c.cc2)
        return self
