# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class USB3(fabll.Node):
    usb3_if = F.USB3_IF.MakeChild()

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # self.usb3_if.gnd_drain.connect(self.usb3_if.usb_if.buspower.lv)
    # self.usb3_if.usb_if.buspower.voltage.constrain_subset(
    #     fabll.Range(4.75 * P.V, 5.5 * P.V)
    # )
