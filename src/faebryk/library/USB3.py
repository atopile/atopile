# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P


class USB3(fabll.Node):
    usb3_if = F.USB3_IF.MakeChild()

    def __preinit__(self):
        self.usb3_if.gnd_drain.connect(self.usb3_if.usb_if.buspower.lv)
        self.usb3_if.usb_if.buspower.voltage.constrain_subset(
            fabll.Range(4.75 * P.V, 5.5 * P.V)
        )
