# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.libs.library import L


class CD4011(F.Logic74xx):
    def __init__(self):
        super().__init__(
            [lambda: F.ElectricLogicGates.NAND(input_cnt=2) for _ in range(4)]
        )

    simple_value_representation = L.f_field(F.has_simple_value_representation_defined)(
        "cd4011"
    )
