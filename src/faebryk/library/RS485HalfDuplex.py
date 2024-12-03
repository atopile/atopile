# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface


class RS485HalfDuplex(ModuleInterface):
    """
    Half-duplex RS485 interface
    A = p
    B = n
    """

    diff_pair: F.DifferentialPair
