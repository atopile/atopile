# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod
from typing import Sequence

import faebryk.library._F as F
from faebryk.core.trait import Trait

logger = logging.getLogger(__name__)


class is_surge_protected(Trait):
    @abstractmethod
    def get_tvs(self) -> Sequence[F.TVS]: ...
