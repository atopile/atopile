# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum

from faebryk.core.core import Footprint
from faebryk.library.can_attach_via_pinmap_equal import can_attach_via_pinmap_equal
from faebryk.library.Electrical import Electrical
from faebryk.library.has_equal_pins_in_ifs import has_equal_pins_in_ifs
from faebryk.libs.util import times


class SMDTwoPin(Footprint):
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

        class _IFs(Footprint.IFS()):
            pins = times(2, Electrical)

        self.IFs = _IFs(self)
        from faebryk.library.has_kicad_footprint_equal_ifs import (
            has_kicad_footprint_equal_ifs,
        )

        class _has_kicad_footprint(has_kicad_footprint_equal_ifs):
            @staticmethod
            def get_kicad_footprint() -> str:
                table = {
                    self.Type._01005: "0402",
                    self.Type._0201: "0603",
                    self.Type._0402: "1005",
                    self.Type._0603: "1005",
                    self.Type._0805: "2012",
                    self.Type._1206: "3216",
                    self.Type._1210: "3225",
                    self.Type._1218: "3246",
                    self.Type._2010: "5025",
                    self.Type._2512: "6332",
                }
                return "Resistor_SMD:R_{imperial}_{metric}Metric".format(
                    imperial=type.name[1:], metric=table[type]
                )

        self.add_trait(_has_kicad_footprint())
        self.add_trait(has_equal_pins_in_ifs())
        self.add_trait(can_attach_via_pinmap_equal())
