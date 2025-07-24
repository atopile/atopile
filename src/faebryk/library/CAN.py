# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface


class CAN(ModuleInterface):
    """
    CAN bus interface
    """

    diff_pair: F.DifferentialPair
