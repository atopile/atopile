# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class SPIFlash(Module):
    power: F.ElectricPower
    qspi = L.f_field(F.MultiSPI)(4)

    memory_size = L.p_field(
        units=P.byte,
        domain=L.Domains.Numbers.NATURAL(),
    )
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def single_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )
