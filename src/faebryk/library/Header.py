# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P
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
        self.pin_count_horizonal.alias_is(self._horizontal_pin_count)
        self.pin_count_vertical.alias_is(self._vertical_pin_count)

    pin_pitch = L.p_field(
        units=P.mm,
        likely_constrained=True,
        domain=L.Domains.Numbers.REAL(),
        soft_set=L.Range(1 * P.mm, 10 * P.mm),
    )
    pin_type = L.p_field(
        domain=L.Domains.ENUM(PinType),
    )
    pad_type = L.p_field(
        domain=L.Domains.ENUM(PadType),
    )
    angle = L.p_field(
        domain=L.Domains.ENUM(Angle),
    )
    pin_count_horizonal = L.p_field(
        domain=L.Domains.Numbers.NATURAL(),
        soft_set=L.Range(2, 100),
    )
    pin_count_vertical = L.p_field(
        domain=L.Domains.Numbers.NATURAL(),
        soft_set=L.Range(2, 100),
    )

    mating_pin_length = L.p_field(
        units=P.mm,
        likely_constrained=True,
        domain=L.Domains.Numbers.REAL(),
        soft_set=L.Range(1 * P.mm, 10 * P.mm),
    )

    @L.rt_field
    def contact(self):
        return times(
            self._horizontal_pin_count * self._vertical_pin_count, F.Electrical
        )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.J
    )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            pinmap={f"{i+1}": self.contact[i] for i in range(len(self.contact))}
        )
