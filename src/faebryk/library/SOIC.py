# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.units import P, Quantity
from faebryk.libs.util import times


class SOIC(F.Footprint):
    def __init__(
        self,
        pin_cnt: int,
        size_xy: tuple[Quantity, Quantity],
        pitch: Quantity,
    ) -> None:
        super().__init__()
        self._pin_cnt = pin_cnt
        self._size_xy = size_xy
        self._pitch = pitch

    @L.rt_field
    def pins(self):
        return times(self._pin_cnt, F.Pad)

    class _has_kicad_footprint(F.has_kicad_footprint_equal_ifs):
        def get_kicad_footprint(self) -> str:
            obj = self.obj
            assert isinstance(obj, SOIC)
            return "Package_SO:SOIC-{leads}_{size_x:.1f}x{size_y:.1f}mm_P{pitch:.2f}mm".format(  # noqa: E501
                leads=obj._pin_cnt,
                size_x=obj._size_xy[0].to(P.mm).m,
                size_y=obj._size_xy[1].to(P.mm).m,
                pitch=obj._pitch.to(P.mm).m,
            )

    kicad_footprint: _has_kicad_footprint
    attach_via_pinmap: F.can_attach_via_pinmap_equal
    equal_pins: F.has_equal_pins_in_ifs
