# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class Filter(Module):
    class Response(Enum):
        LOWPASS = auto()
        HIGHPASS = auto()
        BANDPASS = auto()
        BANDSTOP = auto()
        OTHER = auto()

    cutoff_frequency = L.p_field(
        units=P.Hz,
        likely_constrained=True,
        domain=L.Domains.Numbers.REAL(),
        soft_set=L.Range(0 * P.Hz, 1000 * P.Hz),
    )
    order = L.p_field(
        domain=L.Domains.Numbers.NATURAL(),
        soft_set=L.Range(2, 10),
        guess=2,
    )
    response = L.p_field(
        domain=L.Domains.ENUM(Response),
    )

    in_: F.Signal
    out: F.Signal
