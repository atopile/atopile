# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface


class DifferentialPair(ModuleInterface):
    p: F.SignalElectrical
    n: F.SignalElectrical

    impedance: F.TBD

    def terminated(self) -> Self:
        terminated_bus = type(self)()
        rs = terminated_bus.add_to_container(2, F.Resistor)
        for r in rs:
            r.resistance.merge(self.impedance)

        terminated_bus.p.signal.connect_via(rs[0], self.p.signal)
        terminated_bus.n.signal.connect_via(rs[1], self.n.signal)
        self.connect_shallow(terminated_bus)

        return terminated_bus
