# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.units import Quantity


class DifferentialPair(ModuleInterface):
    p: F.Electrical
    n: F.Electrical

    impedance: F.TBD[Quantity]

    def terminated(self) -> Self:
        terminated_bus = type(self)()
        rs = terminated_bus.add_to_container(2, F.Resistor)
        for r in rs:
            r.resistance.merge(self.impedance)

        terminated_bus.p.connect_via(rs[0], self.p)
        terminated_bus.n.connect_via(rs[1], self.n)
        self.connect_shallow(terminated_bus)

        return terminated_bus
