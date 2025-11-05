# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll  # noqa: F401
import faebryk.library._F as F  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class XtalIF(fabll.Node):
    """
    TODO: Docstring describing your module
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    xin = F.Electrical.MakeChild()
    xout = F.Electrical.MakeChild()
    gnd = F.Electrical.MakeChild()

    @classmethod
    def MakeChild(cls):
        return fabll.ChildField(cls)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        pass

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.xin.add(F.has_net_name("XIN", level=F.has_net_name.Level.SUGGESTED))
        self.xout.add(F.has_net_name("XOUT", level=F.has_net_name.Level.SUGGESTED))
        self.gnd.add(F.has_net_name("GND", level=F.has_net_name.Level.SUGGESTED))
