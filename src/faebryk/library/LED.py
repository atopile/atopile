# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F


class LED(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
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

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    diode = F.Diode.MakeChild()

    brightness = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Candela)
    max_brightness = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Candela)
    color = F.Parameters.EnumParameter.MakeChild(enum_t=Color)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # ----------------------------------------
    #                WIP
    # ----------------------------------------
    # TODO: Implement math and constraints in typegraph
    # def __preinit__(self):
    #     self.current.alias_is(self.brightness / self.max_brightness * self.max_current)
    #     self.brightness.constrain_le(self.max_brightness)

    # def set_intensity(self, intensity: ParameterOperatable.NumberLike) -> None:
    #     self.brightness.alias_is(intensity * self.max_brightness)

    S = F.has_simple_value_representation.Spec
    _simple_repr = fabll.Traits.MakeEdge(
        F.has_simple_value_representation.MakeChild(
            S(max_brightness),
            S(color),
            # S(diode.get().forward_voltage, prefix="Vf"), calling get before instantiation is not allowed
            # S(diode.get().current, prefix="If"),
        )
    )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
            import LED, Resistor, ElectricPower

            led = new LED
            led.forward_voltage = 2.1V +/- 10%
            led.current = 1mA +/- 50%
            led.max_current = 10mA
            led.color = LED.Color.RED
            led.brightness = 100mcd
            led.package = "0603"

            # Connect with current limiting resistor
            res = new Resistor
            power = new ElectricPower
            assert power.voltage within 5V +/- 5%

            assert (power.voltage-led.forward_voltage) / res.resistance within led.current

            power.hv ~> res ~> led ~> power.lv
            """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
