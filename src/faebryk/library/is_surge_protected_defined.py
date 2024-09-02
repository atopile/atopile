# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Sequence

import faebryk.library._F as F

logger = logging.getLogger(__name__)


class is_surge_protected_defined(F.is_surge_protected.impl()):
    def __init__(self, tvss: Sequence[F.TVS]) -> None:
        super().__init__()
        self.tvss = tvss

    def get_tvs(self):
        return self.tvss
