# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import TYPE_CHECKING

import faebryk.core.node as fabll

if TYPE_CHECKING:
    from faebryk.library.Footprint import Footprint


class has_footprint(fabll.Node):
    @abstractmethod
    def get_footprint(self) -> "Footprint": ...
