# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto
from typing import Callable, Sequence

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class Logic74xx(Module):
    class Family(Enum):
        """
        see https://www.ti.com/lit/sg/sdyu001ab/sdyu001ab.pdf?ts=1692776786223
        """

        UC = auto()
        AUP = auto()
        ALVC = auto()
        AUP1T = auto()
        AVC = auto()
        LV1T = auto()
        LVC = auto()
        AC = auto()
        AHC = auto()
        HC = auto()
        LV_A = auto()
        ALB = auto()
        ALVT = auto()
        GTL = auto()
        GTLP = auto()
        LVT = auto()
        VME = auto()
        ABT = auto()
        ABTE = auto()
        ACT = auto()
        AHCT = auto()
        ALS = auto()
        AS = auto()
        BCT = auto()
        F = auto()
        FB = auto()
        FCT = auto()
        HCT = auto()
        LS = auto()
        LV_AT = auto()
        S = auto()
        TTL = auto()
        CD4000 = auto()

    power: F.ElectricPower
    logic_family = L.p_field(domain=L.Domains.ENUM(Family))

    designator = L.f_field(F.has_designator_prefix)(F.has_designator_prefix.Prefix.U)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __init__(
        self,
        gates_factory: Sequence[Callable[[], F.ElectricLogicGate]],
    ) -> None:
        super().__init__()

        self.gates_factory = gates_factory

    @L.rt_field
    def gates(self):
        return [g() for g in self.gates_factory]
