# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P


class Filter(fabll.Node):
    class Response(Enum):
        LOWPASS = auto()
        HIGHPASS = auto()
        BANDPASS = auto()
        BANDSTOP = auto()
        OTHER = auto()

    cutoff_frequency = fabll.p_field(
        units=P.Hz,
        likely_constrained=True,
        domain=fabll.Domains.Numbers.REAL(),
        soft_set=fabll.Range(0 * P.Hz, 1000 * P.Hz),
    )
    order = fabll.p_field(
        domain=fabll.Domains.Numbers.NATURAL(),
        soft_set=fabll.Range(2, 10),
        guess=2,
    )
    response = fabll.p_field(
        domain=fabll.Domains.ENUM(Response),
    )

    in_: F.Signal
    out: F.Signal
