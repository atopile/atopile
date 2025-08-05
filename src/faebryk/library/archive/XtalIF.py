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
