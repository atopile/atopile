# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
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
        ANGLE_90 = auto()

    def __init__(
        self,
        horizonal_pin_count: int,
        vertical_pin_count: int,
    ) -> None:
        super().__init__()
        self._horizontal_pin_count = horizonal_pin_count
        self._vertical_pin_count = vertical_pin_count

    def __preinit__(self):
        self.pin_count_horizonal.merge(self._horizontal_pin_count)
        self.pin_count_vertical.merge(self._vertical_pin_count)

    pin_pitch: F.TBD
    mating_pin_lenght: F.TBD
    conection_pin_lenght: F.TBD
    spacer_height: F.TBD
    pin_type: F.TBD
    pad_type: F.TBD
    angle: F.TBD

    pin_count_horizonal: F.TBD
    pin_count_vertical: F.TBD

    @L.rt_field
    def contact(self):
        return times(
            self._horizontal_pin_count * self._vertical_pin_count, F.Electrical
        )

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.J
    )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            pinmap={f"{i+1}": self.contact[i] for i in range(len(self.contact))}
        )
