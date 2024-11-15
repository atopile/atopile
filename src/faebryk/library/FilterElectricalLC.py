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

    def __preinit__(self) -> None: ...

    @L.rt_field
    def construction_dependency(self):
        class _(F.has_construction_dependency.impl()):
            def _construct(_self):
                if F.Constant(F.Filter.Response.LOWPASS).is_subset_of(self.response):
                    self.response.merge(F.Filter.Response.LOWPASS)

                    # TODO other orders
                    self.order.merge(2)

                    L = self.inductor.inductance
                    C = self.capacitor.capacitance
                    fc = self.cutoff_frequency

                    # TODO requires parameter constraint solving implemented
                    # fc.merge(1 / (2 * math.pi * math.sqrt(C * L)))

                    # instead assume fc being the driving param
                    realistic_C = F.Range(1 * P.pF, 1 * P.mF)
                    L.merge(1 / ((2 * math.pi * fc) ** 2 * realistic_C))
                    C.merge(1 / ((2 * math.pi * fc) ** 2 * L))

                    # TODO consider splitting C / L in a typical way

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
