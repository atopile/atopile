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

    def on_obj_set(self):
        fabll.Traits.create_and_add_instance_to(
            node=self.xin.get(), trait=F.has_net_name
        ).setup(name="XIN", level=F.has_net_name.Level.SUGGESTED)
        fabll.Traits.create_and_add_instance_to(
            node=self.xout.get(), trait=F.has_net_name
        ).setup(name="XOUT", level=F.has_net_name.Level.SUGGESTED)
