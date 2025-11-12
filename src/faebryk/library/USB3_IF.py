# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class USB3_IF(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    usb_if = F.USB2_0_IF.MakeChild()
    rx = F.DifferentialPair.MakeChild()
    tx = F.DifferentialPair.MakeChild()
    gnd_drain = F.Electrical.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()

    # ----------------------------------------
    #                WIP
    # ----------------------------------------
