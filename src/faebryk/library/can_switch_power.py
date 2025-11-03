# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.core.node as fabll
import faebryk.library._F as F


class can_switch_power(fabll.Node):
    @abstractmethod
    def get_logic_in(self) -> F.ElectricLogic: ...
