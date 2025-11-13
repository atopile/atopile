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
    in_: fabll._ChildField[F.Electrical]
    out: fabll._ChildField[F.Electrical]

    cutoff_frequency = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Hertz,
    )
    order = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Natural,
    )
    response = F.Parameters.EnumParameter.MakeChild(enum_t=Response)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
