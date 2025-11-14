# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll  # noqa: F401
import faebryk.library._F as F  # noqa: F401

logger = logging.getLogger(__name__)


class XtalIF(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    xin = F.Electrical.MakeChild()
    xout = F.Electrical.MakeChild()
    gnd = F.Electrical.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    #     self.xin.add(F.has_net_name("XIN", level=F.has_net_name.Level.SUGGESTED))
    #     self.xout.add(F.has_net_name("XOUT", level=F.has_net_name.Level.SUGGESTED))
    #     self.gnd.add(F.has_net_name("GND", level=F.has_net_name.Level.SUGGESTED))
