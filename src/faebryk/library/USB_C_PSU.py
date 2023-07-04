# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.core.util import connect_all_interfaces
from faebryk.library.Constant import Constant
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.Resistor import Resistor
from faebryk.library.USB_Type_C_Receptacle_24_pin import USB_Type_C_Receptacle_24_pin
from faebryk.libs.units import K
from faebryk.libs.util import times


class USB_C_PSU(Module):
    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            power_out = ElectricPower()

        self.IFs = _IFs(self)

        # components
        class _CMPs(Module.NODES()):
            usb = USB_Type_C_Receptacle_24_pin()
            configuration_resistors = times(2, lambda: Resistor(Constant(5.1 * K)))

        self.CMPs = _CMPs(self)

        connect_all_interfaces(
            list(self.CMPs.usb.IFs.vbus + [self.IFs.power_out.NODEs.hv])
        )
        connect_all_interfaces(
            list(self.CMPs.usb.IFs.gnd + [self.IFs.power_out.NODEs.lv])
        )

        # configure as ufp with 5V@max3A
        self.CMPs.usb.IFs.cc1.connect_via(
            self.CMPs.configuration_resistors[0], self.IFs.power_out.NODEs.lv
        )
        self.CMPs.usb.IFs.cc2.connect_via(
            self.CMPs.configuration_resistors[1], self.IFs.power_out.NODEs.lv
        )
