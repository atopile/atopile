# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from enum import IntEnum

from faebryk.core.module import Module


class has_pcb_position(Module.TraitT):
    class layer_type(IntEnum):
        NONE = 0
        TOP_LAYER = -1
        BOTTOM_LAYER = 1

    Point = tuple[float, float, float, layer_type]

    @abstractmethod
    def get_position(self) -> Point: ...
