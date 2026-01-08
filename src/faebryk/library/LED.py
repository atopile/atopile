# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from enum import StrEnum

import faebryk.core.node as fabll
import faebryk.library._F as F


class LED(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    class Color(StrEnum):
        # Primary Colors
        RED = "RED"
        GREEN = "GREEN"
        BLUE = "BLUE"

        # Secondary and Mixed Colors
        YELLOW = "YELLOW"
        ORANGE = "ORANGE"
        PURPLE = "PURPLE"
        CYAN = "CYAN"
        MAGENTA = "MAGENTA"

        # Shades of White
        WHITE = "WHITE"
        WARM_WHITE = "WARM_WHITE"
        COLD_WHITE = "COLD_WHITE"
        NATURAL_WHITE = "NATURAL_WHITE"

        # Other Colors
        EMERALD = "EMERALD"
        AMBER = "AMBER"
        PINK = "PINK"
        LIME = "LIME"
        VIOLET = "VIOLET"

        # Specific LED Colors
        ULTRA_VIOLET = "ULTRA_VIOLET"
        INFRA_RED = "INFRA_RED"

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

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.D)
    )

    _can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeChild(["diode", "anode"], ["diode", "cathode"])
    )

    # ----------------------------------------
    #                WIP
    # ----------------------------------------
    # TODO: Implement math and constraints in typegraph
    # def __preinit__(self):
    #     self.current.alias_is(self.brightness / self.max_brightness *self.max_current)
    #     self.brightness.constrain_le(self.max_brightness)

    # def set_intensity(self, intensity: ParameterOperatable.NumberLike) -> None:
    #     self.brightness.alias_is(intensity * self.max_brightness)

    def on_obj_set(self):
        S = F.has_simple_value_representation.Spec
        fabll.Traits.create_and_add_instance_to(
            node=self, trait=F.has_simple_value_representation
        ).MakeChild(
            S(self.max_brightness),
            S(self.color),
            S(self.diode.get().forward_voltage, prefix="Vf"),
            S(self.diode.get().current, prefix="If"),
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
            """,  # noqa: E501
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
