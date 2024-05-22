# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.Constant import Constant
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.Resistor import Resistor
from faebryk.library.USB_C import USB_C
from faebryk.libs.units import k
from faebryk.libs.util import times


class USB_C_5V_PSU(Module):
    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            power_out = ElectricPower()
            usb = USB_C()

        self.IFs = _IFs(self)

        # components
        class _NODEs(Module.NODES()):
            configuration_resistors = times(
                2,
                lambda: Resistor().builder(
                    lambda r: r.PARAMs.resistance.merge(Constant(5.1 * k))
                ),
            )

        self.NODEs = _NODEs(self)

        self.add_trait(
            has_single_electric_reference_defined(
                ElectricLogic.connect_all_module_references(self)
            )
        )

        # configure as ufp with 5V@max3A
        self.IFs.usb.IFs.cc1.connect_via(
            self.NODEs.configuration_resistors[0], self.IFs.power_out.IFs.lv
        )
        self.IFs.usb.IFs.cc2.connect_via(
            self.NODEs.configuration_resistors[1], self.IFs.power_out.IFs.lv
        )
