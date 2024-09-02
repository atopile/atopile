# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum

import faebryk.library._F as F
from faebryk.libs.library import L


class SMDTwoPin(F.Footprint):
    class Type(Enum):
        _01005 = 0
        _0201 = 1
        _0402 = 2
        _0603 = 3
        _0805 = 4
        _1206 = 5
        _1210 = 6
        _1218 = 7
        _2010 = 8
        _2512 = 9

    def __init__(self, type: Type) -> None:
        super().__init__()
        self._type = type

    pins = L.list_field(2, F.Pad)

    class _has_kicad_footprint(F.has_kicad_footprint_equal_ifs):
        def get_kicad_footprint(self) -> str:
            obj = self.obj
            assert isinstance(obj, SMDTwoPin)
            table = {
                SMDTwoPin.Type._01005: "0402",
                SMDTwoPin.Type._0201: "0603",
                SMDTwoPin.Type._0402: "1005",
                SMDTwoPin.Type._0603: "1608",
                SMDTwoPin.Type._0805: "2012",
                SMDTwoPin.Type._1206: "3216",
                SMDTwoPin.Type._1210: "3225",
                SMDTwoPin.Type._1218: "3246",
                SMDTwoPin.Type._2010: "5025",
                SMDTwoPin.Type._2512: "6332",
            }
            return "Resistor_SMD:R_{imperial}_{metric}Metric".format(
                imperial=obj._type.name[1:], metric=table[obj._type]
            )

    kicad_footprint: _has_kicad_footprint
    equal_pins: F.has_equal_pins_in_ifs
    attach_via_pinmap: F.can_attach_via_pinmap_equal
