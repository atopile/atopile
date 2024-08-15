# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum

from faebryk.core.core import Parameter
from faebryk.library.Constant import Constant
from faebryk.library.Range import Range
from faebryk.libs.units import k, m

"""
luminous intensity in candela (cd)
luminous flux in lumen (lm)
illuminance in lux (lx)

Luminous flux (lm) = Luminous intensity (cd) * Solid angle (sr)
Illuminance (lx) = Luminous flux (lm) / Area (m^2)

https://www.ledrise.eu/blog/led_efficacy_efficencty_explained-lr/

Examples:
A 100-watt light bulb emits about 1,500 lumens of light.
A 23-watt LED emits about 1,500 lumens of light.
A 100-watt light bulb emits about 17 lumens per watt.
A 23-watt LED emits about 65 lumens per watt.

A light bulb with a luminous intensity of 10 candelas emitting light uniformly in all
    directions over a sphere (4π steradians) will have a luminous flux of:
Luminous flux = 10 cd * 4π sr ≈ 125.66 lm

If this luminous flux is distributed evenly over a 10 square meter area,
    the illuminance will be:
Illuminance= 125.66 lm / 10 m2 ≈ 12.57 lux

"""


class _Unit:
    unit: str | None = None

    def __init__(self, value: Parameter[float]):
        assert self.unit
        self._value = value

    def __repr__(self):
        return f"{self._value} {self.unit}"

    @property
    def value(self):
        return self._value.copy()


# Temporary unit classes until faebryk supports units
class LuminousIntensity(_Unit):
    unit = "cd"


class LuminousFlux(_Unit):
    unit = "lm"

    @classmethod
    def from_intensity(
        cls,
        intensity: LuminousIntensity,
        solid_angle: Parameter[float],
    ) -> "LuminousFlux":
        return LuminousFlux(intensity.value * solid_angle)

    def to_intensity(self, solid_angle: Parameter[float]) -> LuminousIntensity:
        return LuminousIntensity(self.value / solid_angle)


class Illuminance(_Unit):
    unit = "lx"

    @classmethod
    def from_flux(cls, flux: LuminousFlux, area: Parameter[float]) -> "Illuminance":
        return Illuminance(flux.value / area)

    def to_luminous_flux(self, area: Parameter[float]) -> LuminousFlux:
        return LuminousFlux(self.value * area)


class TypicalLuminousIntensity(Enum):
    """
    Well known luminous intensities in candela.
    """

    CANDLE = LuminousFlux(Constant(1))

    CREE_SMD_LED_EXTREMELY_DIM = LuminousFlux(Constant(10 * m))
    CREE_SMD_LED_VERY_DIM = LuminousFlux(Constant(25 * m))
    CREE_SMD_LED_DIM = LuminousFlux(Constant(50 * m))
    CREE_SMD_LED_NORMAL = LuminousFlux(Constant(100 * m))
    CREE_SMD_LED_BRIGHT = LuminousFlux(Constant(250 * m))
    CREE_SMD_LED_VERY_BRIGHT = LuminousFlux(Constant(2))
    CREE_SMD_LED_EXTREMELY_BRIGHT = LuminousFlux(Constant(14))

    TYPICAL_SMD_LED_MAX_BRIGHTNESS = LuminousFlux(Range(60 * m, 800 * m))

    WS2812B_LED_RED = LuminousFlux(Constant(420 * m))
    WS2812B_LED_GREEN = LuminousFlux(Constant(720 * m))
    WS2812B_LED_BLUE = LuminousFlux(Constant(200 * m))

    APPLICATION_CAR_HEADLIGHTS_HALOGEN_LOW_BEAM_MEDIUM = LuminousFlux(Constant(20 * k))
    APPLICATION_CAR_HEADLIGHTS_HALOGEN_HIGH_BEAM_MEDIUM = LuminousFlux(Constant(40 * k))
    APPLICATION_CAR_TURN_INDICATOR_DIM = LuminousFlux(Constant(1 * k))
    APPLICATION_CAR_TURN_INDICATOR_BRIGHT = LuminousFlux(Constant(10 * k))
    APPLICATION_CAR_BREAK_LIGHT_DIM = LuminousFlux(Constant(5 * k))
    APPLICATION_CAR_BREAK_LIGHT_BRIGHT = LuminousFlux(Constant(50 * k))

    # not sure about these values
    APPLICATION_LED_STANDBY = LuminousFlux(Range(1 * m, 10 * m))
    APPLICATION_LED_INDICATOR_INSIDE = LuminousFlux(Range(10 * m, 100 * m))
    APPLICATION_LED_KEYBOARD_BACKLIGHT = LuminousFlux(Range(50 * m, 500 * m))
    APPLICATION_LED_INDICATOR_OUTSIDE = LuminousFlux(Range(100 * m, 1))
    APPLICATION_LED_DECORATIVE_LIGHTING = LuminousFlux(Range(100 * m, 1))
    APPLICATION_LED_FLASHLIGHT = LuminousFlux(Range(10, 1 * k))


class TypicalLuminousFlux(Enum):
    """
    Well known luminous flux in lumen.
    """

    IKEA_E14_BULB_LED_DIM = LuminousFlux(Constant(100))
    IKEA_E14_BULB_LED_MEDIUM = LuminousFlux(Constant(250))
    IKEA_E14_BULB_LED_BRIGHT = LuminousFlux(Constant(470))
    IKEA_GU10_BULB_LED_DIM = LuminousFlux(Constant(230))
    IKEA_GU10_BULB_LED_MEDIUM = LuminousFlux(Constant(345))
    IKEA_E27_BULB_LED_DIM = LuminousFlux(Constant(470))
    IKEA_E27_BULB_LED_MEDIUM = LuminousFlux(Constant(806))
    IKEA_E27_BULB_LED_BRIGHT = LuminousFlux(Constant(1500))

    CREE_SMD_LED_VERY_BRIGHT = LuminousFlux(Constant(6000))

    LASER_POINTER_GREEN_5MW = LuminousFlux(Constant(3.4))

    CAR_HEADLIGHTS_HALOGEN_LOW_BEAM_MEDIUM = LuminousFlux(Constant(1000))
    CAR_HEADLIGHTS_HALOGEN_HIGH_BEAM_MEDIUM = LuminousFlux(Constant(1300))


class TypicalIlluminance(Enum):
    """
    Well known illuminances in lux.
    """

    # https://en.wikipedia.org/wiki/Lux
    MOONLESS_OVERCAST_NIGHT_SKY_STARLIGHT = Illuminance(Constant(0.0001))
    MOONLESS_CLEAR_NIGHT_SKY_WITH_AIRGLOW = Illuminance(Constant(0.002))
    FULL_MOON_ON_A_CLEAR_NIGHT = Illuminance(Constant(0.05))
    DARK_LIMIT_OF_CIVIL_TWILIGHT_UNDER_A_CLEAR_SKY = Illuminance(Constant(3.4))
    PUBLIC_AREAS_WITH_DARK_SURROUNDINGS = Illuminance(Constant(20))
    FAMILY_LIVING_ROOM_LIGHTS = Illuminance(Constant(50))
    OFFICE_BUILDING_HALLWAY_TOILET_LIGHTING = Illuminance(Constant(80))
    VERY_DARK_OVERCAST_DAY = Illuminance(Constant(100))
    TRAIN_STATION_PLATFORMS = Illuminance(Constant(150))
    OFFICE_LIGHTING = Illuminance(Constant(320))
    SUNRISE_OR_SUNSET_ON_A_CLEAR_DAY = Illuminance(Constant(400))
    OVERCAST_DAY = Illuminance(Constant(1000))
    FULL_DAYLIGHT = Illuminance(Constant(25000))
    DIRECT_SUNLIGHT = Illuminance(Constant(100000))
