# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import Quantity


class SPIFlash(Module):
    power: F.ElectricPower
    spi = L.f_field(F.MultiSPI)(4)

    memory_size: F.TBD[Quantity]
    designator_prefix = L.f_field(F.has_designator_prefix_defined)("U")
