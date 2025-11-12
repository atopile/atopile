# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class USB2_0_IF(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    d = F.DifferentialPair.MakeChild()
    buspower = F.ElectricPower.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()

    # self.d.p.line.add(F.has_net_name("USB_D", level=F.has_net_name.Level.SUGGESTED))
    # self.d.n.line.add(F.has_net_name("USB_D", level=F.has_net_name.Level.SUGGESTED))
    # self.buspower.hv.add(
    #     F.has_net_name("USB_VBUS", level=F.has_net_name.Level.SUGGESTED)
    # )
