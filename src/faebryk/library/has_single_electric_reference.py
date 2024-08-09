# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from abc import abstractmethod

from faebryk.core.core import NodeTrait
from faebryk.library.ElectricPower import ElectricPower


class has_single_electric_reference(NodeTrait):
    @abstractmethod
    def get_reference(self) -> ElectricPower: ...
