# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class is_decoupled(fabll.Node):
    def __init__(self, capacitor: F.Capacitor):
        super().__init__()
        self._capacitor = capacitor

    @property
    def capacitor(self) -> F.Capacitor:
        return self._capacitor
