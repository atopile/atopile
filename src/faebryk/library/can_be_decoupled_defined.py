# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F

logger = logging.getLogger(__name__)


class can_be_decoupled_defined(F.can_be_decoupled.impl()):
    def __init__(self, hv: F.Electrical, lv: F.Electrical) -> None:
        super().__init__()
        self.hv = hv
        self.lv = lv

    def decouple(self):
        obj = self.obj

        capacitor = obj.add(F.Capacitor(), "capacitor")
        self.hv.connect_via(capacitor, self.lv)

        obj.add_trait(F.is_decoupled_nodes())
        return capacitor

    def is_implemented(self):
        return not self.obj.has_trait(F.is_decoupled)
