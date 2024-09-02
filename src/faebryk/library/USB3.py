# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P


class USB3(ModuleInterface):
    usb3_if: F.USB3_IF

    def __preinit__(self):
        self.usb3_if.gnd_drain.connect(self.usb3_if.usb_if.buspower.lv)
        self.usb3_if.usb_if.buspower.voltage.merge(F.Range(4.75 * P.V, 5.5 * P.V))

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )
