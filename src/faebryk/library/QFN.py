# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.units import P, Quantity
from faebryk.libs.util import times


class QFN(F.Footprint):
    def __init__(
        self,
        pin_cnt: int,
        exposed_thermal_pad_cnt: int,
        size_xy: tuple[Quantity, Quantity],
        pitch: Quantity,
        exposed_thermal_pad_dimensions: tuple[Quantity, Quantity],
        has_thermal_vias: bool,
    ) -> None:
        super().__init__()

        self._pin_cnt = pin_cnt
        self._exposed_thermal_pad_cnt = exposed_thermal_pad_cnt
        self._size_xy = size_xy
        self._pitch = pitch
        self._exposed_thermal_pad_dimensions = exposed_thermal_pad_dimensions
        self._has_thermal_vias = has_thermal_vias

        assert exposed_thermal_pad_cnt > 0 or not has_thermal_vias
        assert (
            exposed_thermal_pad_dimensions[0] < size_xy[0]
            and exposed_thermal_pad_dimensions[1] < size_xy[1]
        )

    @L.rt_field
    def pins(self):
        return times(self._pin_cnt, F.Pad)

    equal_pins: F.has_equal_pins_in_ifs
    attach_via_pinmap: F.can_attach_via_pinmap_equal

    @L.rt_field
    def kicad_footprint(self):
        class _has_kicad_footprint(F.has_kicad_footprint_equal_ifs):
            @staticmethod
            def get_kicad_footprint() -> str:
                return "Package_DFN_QFN:QFN-{leads}-{ep}EP_{size_x}x{size_y}mm_P{pitch}mm_EP{ep_x}x{ep_y}mm{vias}".format(  # noqa: E501
                    leads=self._pin_cnt,
                    ep=self._exposed_thermal_pad_cnt,
                    size_x=self._size_xy[0].to(P.mm).m,
                    size_y=self._size_xy[1].to(P.mm).m,
                    pitch=self._pitch.to(P.mm).m,
                    ep_x=self._exposed_thermal_pad_dimensions[0].to(P.mm).m,
                    ep_y=self._exposed_thermal_pad_dimensions[1].to(P.mm).m,
                    vias="_ThermalVias" if self._has_thermal_vias else "",
                )

        return _has_kicad_footprint()
