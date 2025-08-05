# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.smd import SMDSize


class SMDTwoPin(F.Footprint):
    class Type(StrEnum):
        Resistor = "R"
        Capacitor = "C"
        Inductor = "L"

    def __init__(self, size: SMDSize, type: Type) -> None:
        super().__init__()
        self._size = size
        self._type = type

    pins = L.list_field(2, F.Pad)

    class _has_kicad_footprint(F.has_kicad_footprint_equal_ifs):
        def get_kicad_footprint(self) -> str:
            obj = self.get_obj(SMDTwoPin)
            return "{typename}_SMD:{type}_{imperial}_{metric}Metric".format(
                typename=obj._type.name,
                type=obj._type.value,
                imperial=obj._size.imperial.without_prefix,
                metric=obj._size.metric.without_prefix,
            )

    kicad_footprint: _has_kicad_footprint
    equal_pins: F.has_equal_pins_in_ifs
    attach_via_pinmap: F.can_attach_via_pinmap_equal
