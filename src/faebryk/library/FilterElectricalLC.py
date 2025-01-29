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
    damping_ratio = L.p_field(domain=L.Domains.Numbers.REAL())

    z0 = L.p_field(units=P.ohm)

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
        R = self.inductor.dc_resistance
        fc = self.cutoff_frequency
        damping_ratio = self.damping_ratio

        # TODO other orders & types
        self.order.constrain_subset(2)
        self.response.constrain_subset(F.Filter.Response.LOWPASS)

        # cutoff frequency
        fc.alias_is(1 / (2 * math.pi * (C * Li).operation_sqrt()))
        C.alias_is(1 / (4 * math.pi**2 * fc**2 * Li))
        Li.alias_is(1 / (4 * math.pi**2 * fc**2 * C))

        # damping ratio
        damping_ratio.alias_is(R / 2 * (C / Li).operation_sqrt())
        R.alias_is(2 * damping_ratio / (C / Li).operation_sqrt())
        C.alias_is(4 * damping_ratio**2 * Li / R**2)
        Li.alias_is(C * R**2 / (4 * damping_ratio**2))

        # low pass
        self.in_.line.connect_via(
            (self.inductor, self.capacitor),
            self.in_.reference.lv,
        )

        self.in_.line.connect_via(self.inductor, self.out.line)
