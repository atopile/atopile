# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

from faebryk.core.core import Module
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.TBD import TBD
from faebryk.libs.util import times


class Header(Module):
    class PinType(Enum):
        MALE = auto()
        FEMALE = auto()

    class PadType(Enum):
        THROUGH_HOLE = auto()
        SMD = auto()

    class Angle(Enum):
        STRAIGHT = auto()
        VERTICAL90 = auto()
        HORIZONTAL90 = auto()

    def __init__(
        self,
        horizonal_pin_count: int,
        vertical_pin_count: int,
    ) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            unnamed = times(horizonal_pin_count * vertical_pin_count, Electrical)

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            pin_pitch = TBD[float]()
            pin_type = TBD[self.PinType]()
            pad_type = TBD[self.PadType]()
            angle = TBD[self.Angle]()
            pin_count_horizonal = Constant(horizonal_pin_count)
            pin_count_vertical = Constant(vertical_pin_count)

        self.PARAMs = _PARAMs(self)

        self.add_trait(has_designator_prefix_defined("J"))
