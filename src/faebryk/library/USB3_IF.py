# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleInterface
from faebryk.library.DifferentialPair import DifferentialPair
from faebryk.library.Electrical import Electrical
from faebryk.library.USB2_0_IF import USB2_0_IF


class USB3_IF(ModuleInterface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class IFS(ModuleInterface.IFS()):
            usb_if = USB2_0_IF()
            rx = DifferentialPair()
            tx = DifferentialPair()
            gnd_drain = Electrical()

        self.IFs = IFS(self)
