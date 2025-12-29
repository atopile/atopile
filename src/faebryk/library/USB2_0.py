# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class USB2_0(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    usb_if = F.USB2_0_IF.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # can_bridge allows USB2_0 to be used with ~> operator
    # Points to usb_if for both in and out (passthrough)
    can_bridge = fabll.Traits.MakeEdge(F.can_bridge.MakeEdge(in_=[""], out_=[""]))
