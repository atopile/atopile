# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F


class Filter(fabll.Node):
    class Response(Enum):
        LOWPASS = auto()
        HIGHPASS = auto()
        BANDPASS = auto()
        BANDSTOP = auto()
        OTHER = auto()

    cutoff_frequency = fabll.Parameter.MakeChild_Numeric(
        unit=fabll.Units.Hertz,
    )
    order = fabll.Parameter.MakeChild_Numeric(
        unit=fabll.Units.Natural,
    )
    response = fabll.Parameter.MakeChild_Enum(enum_t=Response)

    in_: fabll.ChildField[F.Electrical]
    out: fabll.ChildField[F.Electrical]
