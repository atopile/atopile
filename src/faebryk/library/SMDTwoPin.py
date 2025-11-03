# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.smd import SMDSize


class SMDTwoPin(fabll.Node):
    class Type(StrEnum):
        Resistor = "R"
        Capacitor = "C"
        Inductor = "L"

    def __init__(self, size: SMDSize, type: Type) -> None:
        super().__init__()
        self._size = size
        self._type = type

    pins = [F.Pad.MakeChild() for _ in range(2)]

    class _has_kicad_footprint(fabll.Node):
        _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

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
