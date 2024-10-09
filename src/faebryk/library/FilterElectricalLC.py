# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import math

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.units import P


class FilterElectricalLC(F.Filter):
    in_: F.SignalElectrical
    out: F.SignalElectrical
    capacitor: F.Capacitor
    inductor: F.Inductor

    z0 = L.p_field(units=P.ohm)

    def __preinit__(self) -> None: ...

    @L.rt_field
    def construction_dependency(self):
        class _(F.has_construction_dependency.impl()):
            def _construct(_self):
                if F.Constant(F.Filter.Response.LOWPASS).is_subset_of(self.response):
                    # TODO other orders & types
                    self.order.constrain_subset(2)
                    self.response.constrain_subset(F.Filter.Response.LOWPASS)

                    Li = self.inductor.inductance
                    C = self.capacitor.capacitance
                    fc = self.cutoff_frequency

                    fc.alias_is(1 / (2 * math.pi * (C * Li).operation_sqrt()))

                    # low pass
                    self.in_.signal.connect_via(
                        (self.inductor, self.capacitor),
                        self.in_.reference.lv,
                    )

                    self.in_.signal.connect_via(self.inductor, self.out.signal)
                    return

                if isinstance(self.response, F.Constant):
                    raise F.has_construction_dependency.NotConstructableEver()

                raise F.has_construction_dependency.NotConstructableYet()

        return _()
