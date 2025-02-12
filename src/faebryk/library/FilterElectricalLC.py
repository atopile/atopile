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


class FilterElectricalLC(F.Filter):
    """
    Basic Electrical LC filter
    """

    in_: F.ElectricSignal
    out: F.ElectricSignal
    capacitor: F.Capacitor
    inductor: F.Inductor
    characteristic_impedance = L.p_field(units=P.ohm)

    def __preinit__(self):
        (
            self.response.operation_is_subset(F.Filter.Response.LOWPASS)
            & self.order.operation_is_subset(2)
        ).if_then_else(
            self.build_lowpass,
            lambda: raise_(NotImplementedError()),
            preference=True,
        )

        # TODO add construction dependency trait

    # TODO make private
    @once
    def build_lowpass(self):
        Li = self.inductor.inductance
        C = self.capacitor.capacitance
        z0 = self.characteristic_impedance
        fc = self.cutoff_frequency

        # TODO other orders & types
        self.order.constrain_subset(2)
        self.response.constrain_subset(F.Filter.Response.LOWPASS)

        z0.alias_is((Li / C).operation_sqrt())
        fc.alias_is(1 / (2 * math.pi * (C * Li).operation_sqrt()))

        # alternative formulations as hints for solver
        # TODO: make the solver powerful enough that these aren't needed

        # characteristic impedance
        Li.alias_is(z0**2 * C)
        C.alias_is(Li / z0**2)

        # cutoff frequency
        C.alias_is(1 / (4 * math.pi**2 * fc**2 * Li))
        Li.alias_is(1 / (4 * math.pi**2 * fc**2 * C))

        # substituted
        Li.alias_is(z0 / (2 * math.pi * fc))
        C.alias_is(1 / (2 * math.pi * fc * z0))

        # low pass
        self.in_.line.connect_via(
            (self.inductor, self.capacitor),
            self.in_.reference.lv,
        )

        self.in_.line.connect_via(self.inductor, self.out.line)
