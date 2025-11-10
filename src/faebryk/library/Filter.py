# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F


class Filter(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    class Response(Enum):
        LOWPASS = auto()
        HIGHPASS = auto()
        BANDPASS = auto()
        BANDSTOP = auto()
        OTHER = auto()

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    in_: fabll.ChildField[F.Electrical]
    out: fabll.ChildField[F.Electrical]

    cutoff_frequency = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Hertz,
    )
    order = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Natural,
    )
    response = fabll.Parameter.MakeChild_Enum(enum_t=Response)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.is_module.MakeChild()
