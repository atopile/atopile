# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
import faebryk.libs.library.L as L

logger = logging.getLogger(__name__)


class is_decoupled(L.Trait.decless()):
    def __init__(self, capacitor: F.Capacitor):
        super().__init__()
        self._capacitor = capacitor

    @property
    def capacitor(self) -> F.Capacitor:
        return self._capacitor
