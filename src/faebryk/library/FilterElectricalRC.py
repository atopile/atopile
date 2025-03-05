# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import once

logger = logging.getLogger(__name__)


class FilterElectricalRC(F.Filter):
    """
    Basic Electrical RC filter
    """

    in_: F.ElectricSignal
    out: F.ElectricSignal
    capacitor: F.Capacitor
    resistor: F.Resistor

    z0 = L.p_field(
        units=P.ohm,
        soft_set=L.Range(1000 * P.ohm, 100000 * P.ohm),
    )

    def __preinit__(self):
        self.response.operation_is_subset(F.Filter.Response.LOWPASS)
        self.order.operation_is_subset(1)

    @once
    def build_lowpass(self):
        R = self.resistor.resistance
        C = self.capacitor.capacitance
        fc = self.cutoff_frequency

        self.order.constrain_subset(1)
        self.response.constrain_subset(F.Filter.Response.LOWPASS)

        # Equations
        R.alias_is(self.z0)
        C.alias_is(1 / (2 * math.pi * fc * R))

        # Solve for output
        fc.alias_is(1 / (2 * math.pi * R * C))
        self.z0.alias_is(R)

        # Connections
        self.in_.line.connect_via(
            (self.resistor, self.capacitor),
            self.in_.reference.lv,
        )

        self.in_.line.connect_via(self.resistor, self.out.line)
