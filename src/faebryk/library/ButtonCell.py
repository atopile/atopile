# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from enum import IntEnum, StrEnum

from faebryk.core.core import Parameter
from faebryk.library.Battery import Battery
from faebryk.library.Constant import Constant
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.TBD import TBD
from faebryk.libs.units import P


class ButtonCell(Battery):
    class Material(StrEnum):
        Alkaline = "L"
        SilverOxide = "S"
        ZincAir = "P"
        Lithium = "C"
        Mercury = "M"
        NickelCadmium = "K"
        NickelMetalHydride = "H"

        @property
        def voltage(self) -> Parameter:
            return {
                self.Alkaline: Constant(1.5 * P.V),
                self.SilverOxide: Constant(1.55 * P.V),
                self.ZincAir: Constant(1.65 * P.V),
                self.Lithium: Constant(3.0 * P.V),
                self.Mercury: Constant(1.35 * P.V),
                self.NickelCadmium: Constant(1.2 * P.V),
                self.NickelMetalHydride: Constant(1.2 * P.V),
            }[self]

    class Shape(StrEnum):
        Round = "R"

    class Size(IntEnum):
        L_41 = 41
        L_43 = 43
        L_44 = 44
        L_54 = 54
        N_1025 = 1025
        N_1216 = 1216
        N_1220 = 1220
        N_1225 = 1225
        N_1616 = 1616
        N_1620 = 1620
        N_1632 = 1632
        N_2016 = 2016
        N_2025 = 2025
        N_2032 = 2032
        N_2430 = 2430
        N_2450 = 2450

    def __init__(self) -> None:
        super().__init__()

        class _PARAMs(Battery.PARAMS()):
            material = TBD[self.Material]()
            shape = TBD[self.Shape]()
            size = TBD[self.Size]()

        self.PARAMs = _PARAMs(self)

        self.add_trait(has_designator_prefix_defined("B"))

        # TODO merge voltage with material voltage
