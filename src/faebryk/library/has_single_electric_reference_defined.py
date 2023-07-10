# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_single_electric_reference import has_single_electric_reference


class has_single_electric_reference_defined(has_single_electric_reference.impl()):
    def __init__(self, reference: ElectricPower) -> None:
        super().__init__()
        self.reference = reference

    def get_reference(self) -> ElectricPower:
        return self.reference
