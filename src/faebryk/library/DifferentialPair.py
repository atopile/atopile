# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P


class DifferentialPair(ModuleInterface):
    p: F.SignalElectrical
    n: F.SignalElectrical

    impedance = L.p_field(
        units=P.Ω,
        likely_constrained=True,
        soft_set=L.Range(10 * P.Ω, 100 * P.Ω),
        tolerance_guess=10 * P.percent,
    )

    def terminated(self) -> Self:
        terminated_bus = type(self)()
        rs = terminated_bus.add_to_container(2, F.Resistor)
        for r in rs:
            r.resistance.alias_is(self.impedance)

        terminated_bus.p.signal.connect_via(rs[0], self.p.signal)
        terminated_bus.n.signal.connect_via(rs[1], self.n.signal)
        self.connect_shallow(terminated_bus)

        return terminated_bus
