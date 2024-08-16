# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from enum import Enum, auto

from faebryk.core.core import Parameter
from faebryk.library.Diode import Diode
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.Resistor import Resistor
from faebryk.library.TBD import TBD
from faebryk.libs.units import Quantity


class LED(Diode):
    class Color(Enum):
        RED = auto()
        EMERALD = auto()
        GREEN = auto()
        BLUE = auto()
        YELLOW = auto()
        WHITE = auto()

    @classmethod
    def PARAMS(cls):
        class _PARAMs(super().PARAMS()):
            brightness = TBD[Quantity]()
            max_brightness = TBD[Quantity]()
            color = TBD[cls.Color]()

        return _PARAMs

    def __init__(self) -> None:
        super().__init__()

        self.PARAMs = self.PARAMS()(self)

        self.PARAMs.current.merge(
            self.PARAMs.brightness
            / self.PARAMs.max_brightness
            * self.PARAMs.max_current
        )

    def set_intensity(self, intensity: Parameter[Quantity]) -> None:
        self.PARAMs.brightness.merge(intensity * self.PARAMs.max_brightness)

    def connect_via_current_limiting_resistor(
        self,
        input_voltage: Parameter[Quantity],
        resistor: Resistor,
        target: Electrical,
        low_side: bool,
    ):
        if low_side:
            self.IFs.cathode.connect_via(resistor, target)
        else:
            self.IFs.anode.connect_via(resistor, target)

        resistor.PARAMs.resistance.merge(
            self.get_needed_series_resistance_for_current_limit(input_voltage),
        )

    def connect_via_current_limiting_resistor_to_power(
        self, resistor: Resistor, power: ElectricPower, low_side: bool
    ):
        self.connect_via_current_limiting_resistor(
            power.PARAMs.voltage,
            resistor,
            power.IFs.lv if low_side else power.IFs.hv,
            low_side,
        )
