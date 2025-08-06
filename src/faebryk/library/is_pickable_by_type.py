# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F
import faebryk.libs.library.L as L
from faebryk.core.parameter import Parameter


class is_pickable_by_type(F.is_pickable.decless()):
    class Type(Enum):
        Resistor = auto()
        Capacitor = auto()
        Inductor = auto()
        TVS = auto()
        LED = auto()
        Diode = auto()
        LDO = auto()
        MOSFET = auto()

    def __init__(self, pick_type: Type):
        super().__init__()
        self._pick_type = pick_type

    def get_pick_type(self) -> Type:
        return self._pick_type

    def get_parameters(self) -> dict[str, Parameter]:
        obj = self.get_obj(L.Module)
        params = obj.get_children(direct_only=True, types=(Parameter,))
        return {p.get_name(): p for p in params if p.used_for_picking}
