# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.library.can_bridge import can_bridge
from faebryk.library.ElectricLogic import ElectricLogic


class can_switch_power(can_bridge):
    @abstractmethod
    def get_logic_in(self) -> ElectricLogic: ...
