# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
from faebryk.core.module import Module


class Filter(Module):
    class Response(Enum):
        LOWPASS = auto()
        HIGHPASS = auto()
        BANDPASS = auto()
        BANDSTOP = auto()
        OTHER = auto()

    cutoff_frequency: F.TBD
    order: F.TBD
    response: F.TBD

    in_: F.Signal
    out: F.Signal
