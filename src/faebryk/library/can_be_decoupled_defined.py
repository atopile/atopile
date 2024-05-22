# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Capacitor import Capacitor
from faebryk.library.Electrical import Electrical
from faebryk.library.is_decoupled import is_decoupled
from faebryk.library.is_decoupled_nodes import is_decoupled_nodes

logger = logging.getLogger(__name__)


class can_be_decoupled_defined(can_be_decoupled.impl()):
    def __init__(self, hv: Electrical, lv: Electrical) -> None:
        super().__init__()
        self.hv = hv
        self.lv = lv

    def decouple(self):
        obj = self.get_obj()

        capacitor = Capacitor()
        obj.NODEs.capacitor = capacitor
        self.hv.connect_via(capacitor, self.lv)

        obj.add_trait(is_decoupled_nodes())
        return capacitor

    def is_implemented(self):
        return not self.get_obj().has_trait(is_decoupled)
