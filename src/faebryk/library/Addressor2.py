# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.library._F as F

logger = logging.getLogger(__name__)


class Addressor2(F.Addressor):
    """
    Curried Addressor for ato use
    """

    def __init__(self):
        super().__init__(address_bits=2)
