# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F

logger = logging.getLogger(__name__)


class TVS(F.Diode):
    reverse_breakdown_voltage: F.TBD
