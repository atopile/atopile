# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

import faebryk.core.node as fabll
import faebryk.library._F as F


class Filter(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    class Response(StrEnum):
        LOWPASS = "LOWPASS"
        HIGHPASS = "HIGHPASS"
        BANDPASS = "BANDPASS"
        BANDSTOP = "BANDSTOP"
        OTHER = "OTHER"

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    in_: fabll._ChildField[F.Electrical]
    out: fabll._ChildField[F.Electrical]

    cutoff_frequency = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Hertz,
    )
    order = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Dimensionless, integer=True, negative=False
    )
    response = F.Parameters.EnumParameter.MakeChild(enum_t=Response)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
