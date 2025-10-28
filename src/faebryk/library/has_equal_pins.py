# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_equal_pins(fabll.Node):
    @abstractmethod
    def get_pin_map(self) -> dict[F.Pad, str]: ...
