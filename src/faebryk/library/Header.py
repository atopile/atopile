# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import Quantity
from faebryk.libs.util import times


class Header(Module):
    class PinType(Enum):
        MALE = auto()
        FEMALE = auto()

    class PadType(Enum):
        THROUGH_HOLE = auto()
        SMD = auto()

    class Angle(Enum):
        STRAIGHT = auto()
        VERTICAL90 = auto()
        HORIZONTAL90 = auto()

    def __init__(
        self,
        horizonal_pin_count: int,
        vertical_pin_count: int,
    ) -> None:
        super().__init__()
        self.horizontal_pin_count = horizonal_pin_count
        self.vertical_pin_count = vertical_pin_count

    def __preinit__(self):
        self.pin_count_horizonal.merge(self.horizontal_pin_count)
        self.pin_count_vertical.merge(self.vertical_pin_count)

    pin_pitch: F.TBD[Quantity]
    pin_type: F.TBD[PinType]
    pad_type: F.TBD[PadType]
    angle: F.TBD[Angle]

    pin_count_horizonal: F.TBD[int]
    pin_count_vertical: F.TBD[int]

    @L.rt_field
    def unnamed(self):
        return times(self.horizonal_pin_count * self.vertical_pin_count, F.Electrical)

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("J")
