# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module

logger = logging.getLogger(__name__)


class can_be_decoupled_rails(F.can_be_decoupled.impl()):
    def __init__(self, *rails: F.ElectricPower):
        super().__init__()
        assert rails
        self._rails = rails

    def decouple(
        self,
        owner: Module,
        count: int = 1,
    ) -> F.Capacitor:
        caps = [rail.decoupled.decouple(owner, count) for rail in self._rails]
        # TODO
        return caps[0]
