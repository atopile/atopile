# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum

from faebryk.libs.library import L
from faebryk.libs.units import P, Quantity

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


def luminous_flux_to_intensity(flux: Quantity, solid_angle: Quantity) -> Quantity:
    return flux / solid_angle


def luminous_intensity_to_flux(intensity: Quantity, solid_angle: Quantity) -> Quantity:
    return intensity * solid_angle


def luminous_flux_to_illuminance(flux: Quantity, area: Quantity) -> Quantity:
    return flux / area


def illuminance_to_flux(illuminance: Quantity, area: Quantity) -> Quantity:
    return illuminance * area


class TypicalLuminousIntensity(Enum):
    """
    Well known luminous intensities in candela.
    """

    CANDLE = 1 * P.candela

    CREE_SMD_LED_EXTREMELY_DIM = 10 * P.millicandela
    CREE_SMD_LED_VERY_DIM = 25 * P.millicandela
    CREE_SMD_LED_DIM = 50 * P.millicandela
    CREE_SMD_LED_NORMAL = 100 * P.millicandela
    CREE_SMD_LED_BRIGHT = 250 * P.millicandela
    CREE_SMD_LED_VERY_BRIGHT = 2 * P.candela
    CREE_SMD_LED_EXTREMELY_BRIGHT = 14 * P.candela

    TYPICAL_SMD_LED_MAX_BRIGHTNESS = L.Range(60 * P.millicandela, 800 * P.millicandela)

    WS2812B_LED_RED = 420 * P.millicandela
    WS2812B_LED_GREEN = 720 * P.millicandela
    WS2812B_LED_BLUE = 200 * P.millicandela

    APPLICATION_CAR_HEADLIGHTS_HALOGEN_LOW_BEAM_MEDIUM = 20 * P.kcandela
    APPLICATION_CAR_HEADLIGHTS_HALOGEN_HIGH_BEAM_MEDIUM = 40 * P.kcandela
    APPLICATION_CAR_TURN_INDICATOR_DIM = 1 * P.kcandela
    APPLICATION_CAR_TURN_INDICATOR_BRIGHT = 10 * P.kcandela
    APPLICATION_CAR_BREAK_LIGHT_DIM = 5 * P.kcandela
    APPLICATION_CAR_BREAK_LIGHT_BRIGHT = 50 * P.kcandela

    # not sure about these values
    APPLICATION_LED_STANDBY = L.Range(1 * P.millicandela, 10 * P.millicandela)
    APPLICATION_LED_INDICATOR_INSIDE = L.Range(
        10 * P.millicandela, 100 * P.millicandela
    )
    APPLICATION_LED_KEYBOARD_BACKLIGHT = L.Range(
        50 * P.millicandela, 500 * P.millicandela
    )
    APPLICATION_LED_INDICATOR_OUTSIDE = L.Range(100 * P.millicandela, 1 * P.candela)
    APPLICATION_LED_DECORATIVE_LIGHTING = L.Range(100 * P.millicandela, 1 * P.candela)
    APPLICATION_LED_FLASHLIGHT = L.Range(10 * P.candela, 1 * P.kcandela)


class TypicalLuminousFlux(Enum):
    """
    Well known luminous flux in lumen.
    """

    IKEA_E14_BULB_LED_DIM = 100 * P.lm
    IKEA_E14_BULB_LED_MEDIUM = 250 * P.lm
    IKEA_E14_BULB_LED_BRIGHT = 470 * P.lm
    IKEA_GU10_BULB_LED_DIM = 230 * P.lm
    IKEA_GU10_BULB_LED_MEDIUM = 345 * P.lm
    IKEA_E27_BULB_LED_DIM = 470 * P.lm
    IKEA_E27_BULB_LED_MEDIUM = 806 * P.lm
    IKEA_E27_BULB_LED_BRIGHT = 1500 * P.lm

    CREE_SMD_LED_VERY_BRIGHT = 6000 * P.lm

    LASER_POINTER_GREEN_5MW = 3.4 * P.lm

    CAR_HEADLIGHTS_HALOGEN_LOW_BEAM_MEDIUM = 1000 * P.lm
    CAR_HEADLIGHTS_HALOGEN_HIGH_BEAM_MEDIUM = 1300 * P.lm


class TypicalIlluminance(Enum):
    """
    Well known illuminances in lux.
    """

    # https://en.wikipedia.org/wiki/Lux
    MOONLESS_OVERCAST_NIGHT_SKY_STARLIGHT = 0.0001 * P.lx
    MOONLESS_CLEAR_NIGHT_SKY_WITH_AIRGLOW = 0.002 * P.lx
    FULL_MOON_ON_A_CLEAR_NIGHT = 0.05 * P.lx
    DARK_LIMIT_OF_CIVIL_TWILIGHT_UNDER_A_CLEAR_SKY = 3.4 * P.lx
    PUBLIC_AREAS_WITH_DARK_SURROUNDINGS = 20 * P.lx
    FAMILY_LIVING_ROOM_LIGHTS = 50 * P.lx
    OFFICE_BUILDING_HALLWAY_TOILET_LIGHTING = 80 * P.lx
    VERY_DARK_OVERCAST_DAY = 100 * P.lx
    TRAIN_STATION_PLATFORMS = 150 * P.lx
    OFFICE_LIGHTING = 320 * P.lx
    SUNRISE_OR_SUNSET_ON_A_CLEAR_DAY = 400 * P.lx
    OVERCAST_DAY = 1000 * P.lx
    FULL_DAYLIGHT = 25000 * P.lx
    DIRECT_SUNLIGHT = 100000 * P.lx
