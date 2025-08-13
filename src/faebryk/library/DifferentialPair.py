# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P


class DifferentialPair(ModuleInterface):
    p: F.ElectricSignal
    n: F.ElectricSignal

    impedance = L.p_field(
        units=P.Ω,
        likely_constrained=True,
        soft_set=L.Range(10 * P.Ω, 100 * P.Ω),
        tolerance_guess=10 * P.percent,
    )

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricSignal.connect_all_module_references(self)
        )

    def terminated(self) -> Self:
        terminated_bus = type(self)()
        rs = terminated_bus.add_to_container(2, F.Resistor)
        for r in rs:
            r.resistance.alias_is(self.impedance)

        terminated_bus.p.line.connect_via(rs[0], self.p.line)
        terminated_bus.n.line.connect_via(rs[1], self.n.line)
        self.connect_shallow(terminated_bus)

        return terminated_bus

    def __postinit__(self, *args, **kwargs):
        """Attach required net name suffixes for KiCad differential pair detection.

        Ensures nets associated with the positive and negative lines end with
        `_p` and `_n` respectively. The naming algorithm will append these
        required affixes while still deconflicting names globally.
        """
        super().__postinit__(*args, **kwargs)
        # Apply suffixes to the electrical lines of the signals
        self.p.line.add(F.has_net_name_affix.suffix("_P"))
        self.n.line.add(F.has_net_name_affix.suffix("_N"))
