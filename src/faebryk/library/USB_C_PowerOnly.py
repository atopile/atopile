# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.can_be_surge_protected_defined import (
    can_be_surge_protected_defined,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.USB_C import USB_C


class USB_C_PowerOnly(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class IFS(ModuleInterface.IFS()):
            power = ElectricPower()
            cc1 = Electrical()
            cc2 = Electrical()

        self.IFs = IFS(self)

        self.add_trait(
            can_be_surge_protected_defined(
                self.IFs.power.IFs.lv,
                self.IFs.power.IFs.hv,
                self.IFs.cc1,
                self.IFs.cc2,
            )
        )

        self.add_trait(
            has_single_electric_reference_defined(
                ElectricLogic.connect_all_module_references(self)
            )
        )

    def connect_to_full_usb_c(self, usb_c: USB_C):
        self.IFs.power.connect(usb_c.IFs.usb3.IFs.usb2.IFs.buspower)
        self.IFs.cc1.connect(usb_c.IFs.cc1)
        self.IFs.cc2.connect(usb_c.IFs.cc2)
        return self
