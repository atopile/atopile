# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from enum import Enum, auto

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.units import P


class LED(F.Diode):
    class Color(Enum):
        # Primary Colors
        RED = auto()
        GREEN = auto()
        BLUE = auto()

        # Secondary and Mixed Colors
        YELLOW = auto()
        ORANGE = auto()
        PURPLE = auto()
        CYAN = auto()
        MAGENTA = auto()

        # Shades of White
        WHITE = auto()
        WARM_WHITE = auto()
        COLD_WHITE = auto()
        NATURAL_WHITE = auto()

        # Other Colors
        EMERALD = auto()
        AMBER = auto()
        PINK = auto()
        LIME = auto()
        VIOLET = auto()

        # Specific LED Colors
        ULTRA_VIOLET = auto()
        INFRA_RED = auto()

    brightness = L.p_field(units=P.candela)
    max_brightness = L.p_field(units=P.candela)
    color = L.p_field(domain=L.Domains.ENUM(Color))

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            F.is_pickable_by_type.Type.LED,
            F.Diode().get_trait(F.is_pickable_by_type).get_parameters()
            | {
                "max_brightness": self.max_brightness,
                "color": self.color,
            },
        )

    def __preinit__(self):
        self.current.alias_is(self.brightness / self.max_brightness * self.max_current)
        self.brightness.constrain_le(self.max_brightness)
