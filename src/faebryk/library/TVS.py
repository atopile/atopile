# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.library.Diode import Diode
from faebryk.library.TBD import TBD
from faebryk.libs.units import Quantity

logger = logging.getLogger(__name__)


class TVS(Diode):
    def __init__(self):
        super().__init__()

        class _PARAMs(Diode.PARAMS()):
            reverse_breakdown_voltage = TBD[Quantity]()

        self.PARAMs = _PARAMs(self)
