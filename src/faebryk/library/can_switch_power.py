# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.library._F as F


class can_switch_power(F.can_bridge):
    @abstractmethod
    def get_logic_in(self) -> F.ElectricLogic: ...
