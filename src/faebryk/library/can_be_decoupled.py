# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod

from faebryk.core.core import Trait
from faebryk.library.Capacitor import Capacitor

logger = logging.getLogger(__name__)


# TODO better name
class can_be_decoupled(Trait):
    @abstractmethod
    def decouple(self) -> Capacitor:
        ...
