# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.can_attach_via_pinmap_equal import can_attach_via_pinmap_equal
from faebryk.library.Footprint import Footprint
from faebryk.library.has_equal_pins_in_ifs import has_equal_pins_in_ifs
from faebryk.library.Pad import Pad
from faebryk.libs.util import times


class SOIC(Footprint):
    def __init__(
        self,
        pin_cnt: int,
        size_xy_mm: tuple[float, float],
        pitch_mm: float,
    ) -> None:
        super().__init__()

        class _IFs(Footprint.IFS()):
            pins = times(pin_cnt, Pad)

        self.IFs = _IFs(self)
        from faebryk.library.has_kicad_footprint_equal_ifs import (
            has_kicad_footprint_equal_ifs,
        )

        class _has_kicad_footprint(has_kicad_footprint_equal_ifs):
            @staticmethod
            def get_kicad_footprint() -> str:
                return "Package_SO:SOIC-{leads}_{size_x:.1f}x{size_y:.1f}mm_P{pitch:.2f}mm".format(  # noqa: E501
                    leads=pin_cnt,
                    size_x=size_xy_mm[0],
                    size_y=size_xy_mm[1],
                    pitch=pitch_mm,
                )

        self.add_trait(_has_kicad_footprint())
        self.add_trait(has_equal_pins_in_ifs())
        self.add_trait(can_attach_via_pinmap_equal())
