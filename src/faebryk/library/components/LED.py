# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from enum import Enum, StrEnum, auto

from deprecated import deprecated

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import ParameterOperatable
from faebryk.libs.library import L
from faebryk.libs.units import P


class LED(Module):
    """
    We know LEDs are diodes
    """
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

    rated_forward_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.V, 1 * P.V),
        tolerance_guess=10 * P.percent,
    )
    """
    The maximumrated forward voltage drop at the rated forward current.
    """
    rated_forward_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.mA, 10 * P.A),
    )
    """
    Rated continuous forward current.
    """
    rated_power_dissipation = L.p_field(
        units=P.W,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.mW, 10 * P.W),
        tolerance_guess=10 * P.percent,
    )
    """
    Rated power dissipation.
    """

    anode: F.Electrical
    cathode: F.Electrical

    rated_brightness = L.p_field(units=P.cd)
    color = L.p_field(domain=L.Domains.ENUM(Color))

    pickable: F.is_pickable_by_type

    def __init__(self, color: Color):
        super().__init__()
        self.color = color

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.anode, self.cathode)

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.LED
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.anode: ["A", "Anode", "+"],
                self.cathode: ["K", "C", "Cathode", "-"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import LED, Resistor, ElectricPower

        led = new LED
        led.forward_voltage = 2.1V +/- 10%
        led.current = 20mA +/- 5%
        led.max_current = 30mA
        led.color = LED.Color.RED
        led.brightness = 100mcd
        led.package = "0603"

        # Connect with current limiting resistor
        current_resistor = new Resistor
        power_supply = new ElectricPower
        assert power_supply.voltage within 5V +/- 5%

        power_supply.hv ~> current_resistor ~> led ~> power_supply.lv

        # Alternative: use dedicated function
        led.connect_via_current_limiting_resistor(
            power_supply.voltage,
            current_resistor,
            power_supply.lv,
            low_side=True
        )
        """,
        language=F.has_usage_example.Language.ato,
    )

    class Package(StrEnum):
        _01005 = "PACKAGE"

    package = L.p_field(domain=L.Domains.ENUM(Package))
