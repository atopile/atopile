# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING

import faebryk.library._F as F

if TYPE_CHECKING:
    from faebryk.library.ElectricPower import ElectricPower


class has_single_electric_reference_defined(F.has_single_electric_reference.impl()):
    def __init__(self, reference: "ElectricPower") -> None:
        super().__init__()
        self.reference = reference

    def get_reference(self) -> "ElectricPower":
        return self.reference
