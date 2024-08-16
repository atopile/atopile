# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.Range import Range
from faebryk.library.USB3_IF import USB3_IF
from faebryk.libs.units import P


class USB3(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class IFS(ModuleInterface.IFS()):
            usb3_if = USB3_IF()

        self.IFs = IFS(self)

        self.IFs.usb3_if.IFs.gnd_drain.connect(
            self.IFs.usb3_if.IFs.usb_if.IFs.buspower.IFs.lv
        )

        self.IFs.usb3_if.IFs.usb_if.IFs.buspower.PARAMs.voltage.merge(
            Range(4.75 * P.V, 5.5 * P.V)
        )
