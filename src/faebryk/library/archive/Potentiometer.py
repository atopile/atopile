# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class Potentiometer(Module):
    resistors_ifs = L.list_field(2, F.Electrical)
    wiper: F.Electrical
    total_resistance = L.p_field(units=P.ohm)
    resistors = L.list_field(2, F.Resistor)

    def __preinit__(self):
        for i, resistor in enumerate(self.resistors):
            self.resistors_ifs[i].connect_via(resistor, self.wiper)

        self.total_resistance.alias_is(
            self.resistors[0].resistance + self.resistors[1].resistance
        )

    def connect_as_voltage_divider(
        self, high: F.Electrical, low: F.Electrical, out: F.Electrical
    ):
        self.resistors_ifs[0].connect(high)
        self.resistors_ifs[1].connect(low)
        self.wiper.connect(out)

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Potentiometer, ElectricPower, Electrical

        potentiometer = new Potentiometer
        potentiometer.total_resistance = 10kohm +/- 5%

        power_supply = new ElectricPower
        output_voltage = new Electrical

        # Use as voltage divider
        power_supply.hv ~ potentiometer.resistors_ifs[0]
        power_supply.lv ~ potentiometer.resistors_ifs[1]
        output_voltage ~ potentiometer.wiper
        """,
        language=F.has_usage_example.Language.ato,
    )
