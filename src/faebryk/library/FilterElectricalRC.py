# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math

import faebryk.library._F as F

logger = logging.getLogger(__name__)


class FilterElectricalRC(F.Filter):
    """
    Basic Electrical RC filter
    """

    in_: F.ElectricSignal
    out: F.ElectricSignal
    resistor: F.Resistor
    capacitor: F.Capacitor

    def __preinit__(self):
        self.response.alias_is(F.Filter.Response.LOWPASS)
        self.order.alias_is(1)

        R = self.resistor.resistance
        C = self.capacitor.capacitance
        fc = self.cutoff_frequency

        # Equations
        C.alias_is(1 / (R * 2 * math.pi * fc))
        R.alias_is(1 / (C * 2 * math.pi * fc))
        fc.alias_is(1 / (2 * math.pi * R * C))

        # Connections
        self.in_.line.connect_via(
            (self.resistor, self.capacitor),
            self.in_.reference.lv,
        )

        self.in_.line.connect_via(self.resistor, self.out.line)

        # Set the max voltage of the capacitor to min 1.5 times the output voltage
        self.capacitor.max_voltage.constrain_ge(self.out.reference.voltage * 1.5)
