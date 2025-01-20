# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class RJ45_Receptacle(Module):
    class Mounting(Enum):
        TH = auto()
        SMD = auto()

    # interfaces

    pin = L.list_field(8, F.Electrical)
    shield: F.Electrical

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.J
    )
    mounting = L.p_field(domain=L.Domains.ENUM(Mounting))
