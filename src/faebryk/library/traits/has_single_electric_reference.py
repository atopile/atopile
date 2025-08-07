# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from abc import abstractmethod
from typing import TYPE_CHECKING

from faebryk.core.trait import Trait

if TYPE_CHECKING:
    from faebryk.library.ElectricPower import ElectricPower


class has_single_electric_reference(Trait):
    @abstractmethod
    def get_reference(self) -> "ElectricPower": ...
