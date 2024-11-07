# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from enum import IntEnum, StrEnum

import faebryk.library._F as F
from faebryk.core.parameter import Parameter
from faebryk.libs.library import L
from faebryk.libs.units import P


class ButtonCell(F.Battery):
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
                self.Alkaline: F.Constant(1.5 * P.V),
                self.SilverOxide: F.Constant(1.55 * P.V),
                self.ZincAir: F.Constant(1.65 * P.V),
                self.Lithium: F.Constant(3.0 * P.V),
                self.Mercury: F.Constant(1.35 * P.V),
                self.NickelCadmium: F.Constant(1.2 * P.V),
                self.NickelMetalHydride: F.Constant(1.2 * P.V),
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

    material: F.TBD
    shape: F.TBD
    size: F.TBD

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.B
    )

    # TODO merge voltage with material voltage
