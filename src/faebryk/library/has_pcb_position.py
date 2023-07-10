# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from enum import Enum

from faebryk.core.core import ModuleTrait


class has_pcb_position(ModuleTrait):
    class layer_type(Enum):
        NONE = 1
        TOP_LAYER = 2
        BOTTOM_LAYER = 3

    Point = tuple[float, float]

    @abstractmethod
    def get_position(self) -> Point:
        ...
