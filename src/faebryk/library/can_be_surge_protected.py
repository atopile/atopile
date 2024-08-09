# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod
from typing import Sequence

from faebryk.core.core import Trait
from faebryk.library.TVS import TVS

logger = logging.getLogger(__name__)


class can_be_surge_protected(Trait):
    @abstractmethod
    def protect(self) -> Sequence[TVS]: ...
