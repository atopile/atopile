# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.parameter import ParameterOperatable
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

    pickable = L.f_field(F.is_pickable_by_type)(F.is_pickable_by_type.Type.LED)

    def __preinit__(self):
        self.current.alias_is(self.brightness / self.max_brightness * self.max_current)
        self.brightness.constrain_le(self.max_brightness)

    def set_intensity(self, intensity: ParameterOperatable.NumberLike) -> None:
        self.brightness.alias_is(intensity * self.max_brightness)

    def connect_via_current_limiting_resistor(
        self,
        input_voltage: ParameterOperatable.NumberLike,
        resistor: F.Resistor,
        target: F.Electrical,
        low_side: bool,
    ):
        if low_side:
            self.cathode.connect_via(resistor, target)
        else:
            self.anode.connect_via(resistor, target)

        resistor.resistance.alias_is(
            self.get_needed_series_resistance_for_current_limit(input_voltage),
        )
        resistor.allow_removal_if_zero()

    def connect_via_current_limiting_resistor_to_power(
        self, resistor: F.Resistor, power: F.ElectricPower, low_side: bool
    ):
        if low_side:
            self.anode.connect(power.hv)
        else:
            self.cathode.connect(power.lv)

        self.connect_via_current_limiting_resistor(
            power.voltage,
            resistor,
            power.lv if low_side else power.hv,
            low_side,
        )
