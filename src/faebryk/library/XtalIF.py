# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class XtalIF(ModuleInterface):
    """
    TODO: Docstring describing your module
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    xin: F.Electrical
    xout: F.Electrical
    gnd: F.Electrical

    # ----------------------------------------
    #                 traits
    # ----------------------------------------

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
