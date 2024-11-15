# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.libs.util import cast_assert

logger = logging.getLogger(__name__)


class is_decoupled_nodes(F.is_decoupled.impl()):
    def on_obj_set(self) -> None:
        assert "capacitor" in self.obj.runtime

    def get_capacitor(self) -> F.Capacitor:
        return cast_assert(F.Capacitor, self.obj.runtime["capacitor"])
