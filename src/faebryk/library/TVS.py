# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.library.Diode import Diode
from faebryk.library.TBD import TBD

logger = logging.getLogger(__name__)


class TVS(Diode):
    def __init__(self):
        super().__init__()

        class _PARAMs(Diode.PARAMS()):
            reverse_breakdown_voltage = TBD()

        self.PARAMs = _PARAMs(self)
