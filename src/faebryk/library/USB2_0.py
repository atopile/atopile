# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class USB2_0(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    usb_if = F.USB2_0_IF.MakeChild()

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
