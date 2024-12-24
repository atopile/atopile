# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F


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
