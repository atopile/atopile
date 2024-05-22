# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto
from typing import Callable, Sequence

from faebryk.core.core import Module
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricLogicGate import ElectricLogicGate
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.TBD import TBD


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

    def __init__(
        self,
        gates_factory: Sequence[Callable[[], ElectricLogicGate]],
    ) -> None:
        super().__init__()

        class _IFs(Module.IFS()):
            power = ElectricPower()

        self.IFs = _IFs(self)

        class _NODEs(Module.NODES()):
            gates = [g() for g in gates_factory]

        self.NODEs = _NODEs(self)

        class _PARAMs(Module.PARAMS()):
            logic_family = TBD[Logic74xx.Family]()

        self.PARAMs = _PARAMs(self)

        self.add_trait(has_designator_prefix_defined("U"))

        self.add_trait(
            has_single_electric_reference_defined(
                ElectricLogic.connect_all_module_references(self)
            )
        )
