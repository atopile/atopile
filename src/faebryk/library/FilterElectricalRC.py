# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

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

    def __preinit__(self): ...

    @L.rt_field
    def construction_dependency(self):
        class _(F.has_construction_dependency.impl()):
            def _construct(_self):
                if F.Constant(F.Filter.Response.LOWPASS).is_subset_of(self.response):
                    # TODO other orders, types
                    self.order.constrain_subset(L.Single(1))
                    self.response.constrain_subset(L.Single(F.Filter.Response.LOWPASS))

                    R = self.resistor.resistance
                    C = self.capacitor.capacitance
                    fc = self.cutoff_frequency

                    fc.alias_is(1 / (2 * math.pi * R * C))

                    # low pass
                    self.in_.signal.connect_via(
                        (self.resistor, self.capacitor),
                        self.in_.reference.lv,
                    )

                    self.in_.signal.connect_via(self.resistor, self.out.signal)
                    return

                if isinstance(self.response, F.Constant):
                    raise F.has_construction_dependency.NotConstructableEver()

                raise F.has_construction_dependency.NotConstructableYet()

        return _()
