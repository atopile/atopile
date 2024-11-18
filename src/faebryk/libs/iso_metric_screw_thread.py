# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from enum import Enum

logger = logging.getLogger(__name__)


class Iso262_MetricScrewThreadSizes(Enum):
    # TODO add tolerance etc
    # i think values are wrong, but api is ok
    M1 = 1.2
    M1_2 = 1.4
    M1_4 = 1.6
    M1_6 = 1.8
    M1_8 = 2.0
    M2 = 2.2
    M2_5 = 2.7
    M3 = 3.2
    M3_5 = 3.7
    M4 = 4.3
    M5 = 5.3
    M6 = 6.4
    M8 = 8.4
    M10 = 10.4
    M12 = 12.4
    M14 = 14.4
    M16 = 16.4
    M20 = 20.4
    M24 = 24.4
    M30 = 30.4
    M36 = 36.4
    M42 = 42.4
    M48 = 48.4
    M56 = 56.4
    M60 = 60.4
    M64 = 64.4
