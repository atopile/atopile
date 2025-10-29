# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from abc import abstractmethod
from typing import TYPE_CHECKING

import faebryk.core.node as fabll

if TYPE_CHECKING:
    from faebryk.library.ElectricPower import ElectricPower


class has_single_electric_reference(fabll.Node):
    @abstractmethod
    def get_reference(self) -> "ElectricPower": ...
