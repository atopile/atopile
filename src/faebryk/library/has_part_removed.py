# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F

logger = logging.getLogger(__name__)


class has_part_removed(F.has_part_picked):
    def __init__(self):
        super().__init__(None)
