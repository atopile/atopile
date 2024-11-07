# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from copy import copy
from enum import Enum

import faebryk.library._F as F
from faebryk.core.parameter import Parameter
from faebryk.libs.units import P

"""
luminous intensity in candela (candela)
luminous flux in lumen (lm)
illuminance in lux (lx)

Luminous flux (lm) = Luminous intensity (candela) * Solid angle (sr)
Illuminance (lx) = Luminous flux (lm) / Area (m^2)

https://www.ledrise.eu/blog/led_efficacy_efficencty_explained-lr/

Examples:
A 100-watt light bulb emits about 1,500 lumens of light.
A 23-watt LED emits about 1,500 lumens of light.
A 100-watt light bulb emits about 17 lumens per watt.
A 23-watt LED emits about 65 lumens per watt.

A light bulb with a luminous intensity of 10 candelas emitting light uniformly in all
    directions over a sphere (4π steradians) will have a luminous flux of:
Luminous flux = 10 candela * 4π sr ≈ 125.66 lm

If this luminous flux is distributed evenly over a 10 square meter area,
    the illuminance will be:
Illuminance= 125.66 lm / 10 m2 ≈ 12.57 lux

"""


class _Unit:
    def __init__(self, value: Parameter):
        self._value = value

    def __repr__(self):
        return f"{self._value!r}"

    @property
    def value(self):
        return copy(self._value)


# Temporary unit classes until faebryk supports units
class LuminousIntensity(_Unit):
    pass


class LuminousFlux(_Unit):
    @classmethod
    def from_intensity(
        cls,
        intensity: LuminousIntensity,
        solid_angle: Parameter,
    ) -> "LuminousFlux":
        return LuminousFlux(intensity.value * solid_angle)

    def to_intensity(self, solid_angle: Parameter) -> LuminousIntensity:
        return LuminousIntensity(self.value / solid_angle)


class Illuminance(_Unit):
    @classmethod
    def from_flux(cls, flux: LuminousFlux, area: Parameter) -> "Illuminance":
        return Illuminance(flux.value / area)

    def to_luminous_flux(self, area: Parameter) -> LuminousFlux:
        return LuminousFlux(self.value * area)


class TypicalLuminousIntensity(Enum):
    """
    Well known luminous intensities in candela.
    """

    CANDLE = LuminousFlux(F.Constant(1 * P.candela))

    CREE_SMD_LED_EXTREMELY_DIM = LuminousFlux(F.Constant(10 * P.millicandela))
    CREE_SMD_LED_VERY_DIM = LuminousFlux(F.Constant(25 * P.millicandela))
    CREE_SMD_LED_DIM = LuminousFlux(F.Constant(50 * P.millicandela))
    CREE_SMD_LED_NORMAL = LuminousFlux(F.Constant(100 * P.millicandela))
    CREE_SMD_LED_BRIGHT = LuminousFlux(F.Constant(250 * P.millicandela))
    CREE_SMD_LED_VERY_BRIGHT = LuminousFlux(F.Constant(2 * P.candela))
    CREE_SMD_LED_EXTREMELY_BRIGHT = LuminousFlux(F.Constant(14 * P.candela))

    TYPICAL_SMD_LED_MAX_BRIGHTNESS = LuminousFlux(
        F.Range(60 * P.millicandela, 800 * P.mcandela)
    )

    WS2812B_LED_RED = LuminousFlux(F.Constant(420 * P.millicandela))
    WS2812B_LED_GREEN = LuminousFlux(F.Constant(720 * P.millicandela))
    WS2812B_LED_BLUE = LuminousFlux(F.Constant(200 * P.millicandela))

    APPLICATION_CAR_HEADLIGHTS_HALOGEN_LOW_BEAM_MEDIUM = LuminousFlux(
        F.Constant(20 * P.kcandela)
    )
    APPLICATION_CAR_HEADLIGHTS_HALOGEN_HIGH_BEAM_MEDIUM = LuminousFlux(
        F.Constant(40 * P.kcandela)
    )
    APPLICATION_CAR_TURN_INDICATOR_DIM = LuminousFlux(F.Constant(1 * P.kcandela))
    APPLICATION_CAR_TURN_INDICATOR_BRIGHT = LuminousFlux(F.Constant(10 * P.kcandela))
    APPLICATION_CAR_BREAK_LIGHT_DIM = LuminousFlux(F.Constant(5 * P.kcandela))
    APPLICATION_CAR_BREAK_LIGHT_BRIGHT = LuminousFlux(F.Constant(50 * P.kcandela))

    # not sure about these values
    APPLICATION_LED_STANDBY = LuminousFlux(F.Range(1 * P.millicandela, 10 * P.mcandela))
    APPLICATION_LED_INDICATOR_INSIDE = LuminousFlux(
        F.Range(10 * P.millicandela, 100 * P.mcandela)
    )
    APPLICATION_LED_KEYBOARD_BACKLIGHT = LuminousFlux(
        F.Range(50 * P.millicandela, 500 * P.mcandela)
    )
    APPLICATION_LED_INDICATOR_OUTSIDE = LuminousFlux(
        F.Range(100 * P.millicandela, 1 * P.candela)
    )
    APPLICATION_LED_DECORATIVE_LIGHTING = LuminousFlux(
        F.Range(100 * P.millicandela, 1 * P.candela)
    )
    APPLICATION_LED_FLASHLIGHT = LuminousFlux(F.Range(10 * P.candela, 1 * P.kcandela))


class TypicalLuminousFlux(Enum):
    """
    Well known luminous flux in lumen.
    """

    IKEA_E14_BULB_LED_DIM = LuminousFlux(F.Constant(100 * P.lm))
    IKEA_E14_BULB_LED_MEDIUM = LuminousFlux(F.Constant(250 * P.lm))
    IKEA_E14_BULB_LED_BRIGHT = LuminousFlux(F.Constant(470 * P.lm))
    IKEA_GU10_BULB_LED_DIM = LuminousFlux(F.Constant(230 * P.lm))
    IKEA_GU10_BULB_LED_MEDIUM = LuminousFlux(F.Constant(345 * P.lm))
    IKEA_E27_BULB_LED_DIM = LuminousFlux(F.Constant(470 * P.lm))
    IKEA_E27_BULB_LED_MEDIUM = LuminousFlux(F.Constant(806 * P.lm))
    IKEA_E27_BULB_LED_BRIGHT = LuminousFlux(F.Constant(1500 * P.lm))

    CREE_SMD_LED_VERY_BRIGHT = LuminousFlux(F.Constant(6000 * P.lm))

    LASER_POINTER_GREEN_5MW = LuminousFlux(F.Constant(3.4 * P.lm))

    CAR_HEADLIGHTS_HALOGEN_LOW_BEAM_MEDIUM = LuminousFlux(F.Constant(1000 * P.lm))
    CAR_HEADLIGHTS_HALOGEN_HIGH_BEAM_MEDIUM = LuminousFlux(F.Constant(1300 * P.lm))


class TypicalIlluminance(Enum):
    """
    Well known illuminances in lux.
    """

    # https://en.wikipedia.org/wiki/Lux
    MOONLESS_OVERCAST_NIGHT_SKY_STARLIGHT = Illuminance(F.Constant(0.0001 * P.lx))
    MOONLESS_CLEAR_NIGHT_SKY_WITH_AIRGLOW = Illuminance(F.Constant(0.002 * P.lx))
    FULL_MOON_ON_A_CLEAR_NIGHT = Illuminance(F.Constant(0.05 * P.lx))
    DARK_LIMIT_OF_CIVIL_TWILIGHT_UNDER_A_CLEAR_SKY = Illuminance(F.Constant(3.4 * P.lx))
    PUBLIC_AREAS_WITH_DARK_SURROUNDINGS = Illuminance(F.Constant(20 * P.lx))
    FAMILY_LIVING_ROOM_LIGHTS = Illuminance(F.Constant(50 * P.lx))
    OFFICE_BUILDING_HALLWAY_TOILET_LIGHTING = Illuminance(F.Constant(80 * P.lx))
    VERY_DARK_OVERCAST_DAY = Illuminance(F.Constant(100 * P.lx))
    TRAIN_STATION_PLATFORMS = Illuminance(F.Constant(150 * P.lx))
    OFFICE_LIGHTING = Illuminance(F.Constant(320 * P.lx))
    SUNRISE_OR_SUNSET_ON_A_CLEAR_DAY = Illuminance(F.Constant(400 * P.lx))
    OVERCAST_DAY = Illuminance(F.Constant(1000 * P.lx))
    FULL_DAYLIGHT = Illuminance(F.Constant(25000 * P.lx))
    DIRECT_SUNLIGHT = Illuminance(F.Constant(100000 * P.lx))
