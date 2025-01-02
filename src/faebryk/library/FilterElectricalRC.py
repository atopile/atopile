# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math

from more_itertools import raise_

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import once

logger = logging.getLogger(__name__)


class FilterElectricalRC(F.Filter):
    """
    Basic Electrical RC filter
    """

    in_: F.SignalElectrical
    out: F.SignalElectrical
    capacitor: F.Capacitor
    resistor: F.Resistor

    z0 = L.p_field(units=P.ohm)

    def __preinit__(self):
        (
            self.response.operation_is_subset(F.Filter.Response.LOWPASS)
            & self.order.operation_is_subset(1)
        ).if_then_else(
            self.build_lowpass,
            lambda: raise_(NotImplementedError()),
            preference=True,
        )

        # TODO add construction dependency trait

    # TODO make private
    @once
    def build_lowpass(self):
        R = self.resistor.resistance
        C = self.capacitor.capacitance
        fc = self.cutoff_frequency

        # TODO other orders, types
        self.order.constrain_subset(1)
        self.response.constrain_subset(F.Filter.Response.LOWPASS)

        fc.alias_is(1 / (2 * math.pi * R * C))

        # low pass
        self.in_.signal.connect_via(
            (self.resistor, self.capacitor),
            self.in_.reference.lv,
        )

        self.in_.signal.connect_via(self.resistor, self.out.signal)
