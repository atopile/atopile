# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.library.Capacitor import Capacitor
from faebryk.library.is_decoupled import is_decoupled

logger = logging.getLogger(__name__)


class is_decoupled_nodes(is_decoupled.impl()):
    def on_obj_set(self) -> None:
        assert hasattr(self.get_obj().NODEs, "capacitor")

    def get_capacitor(self) -> Capacitor:
        return self.get_obj().NODEs.capacitor
