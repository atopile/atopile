# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.can_attach_via_pinmap_equal import can_attach_via_pinmap_equal
from faebryk.library.Footprint import Footprint
from faebryk.library.has_equal_pins_in_ifs import has_equal_pins_in_ifs
from faebryk.library.Pad import Pad
from faebryk.libs.util import times


class QFN(Footprint):
    def __init__(
        self,
        pin_cnt: int,
        exposed_thermal_pad_cnt: int,
        size_xy_mm: tuple[float, float],
        pitch_mm: float,
        exposed_thermal_pad_dimensions_mm: tuple[float, float],
        has_thermal_vias: bool,
    ) -> None:
        super().__init__()

        class _IFs(Footprint.IFS()):
            pins = times(pin_cnt, Pad)

        self.IFs = _IFs(self)
        assert exposed_thermal_pad_cnt > 0 or not has_thermal_vias
        assert (
            exposed_thermal_pad_dimensions_mm[0] < size_xy_mm[0]
            and exposed_thermal_pad_dimensions_mm[1] < size_xy_mm[1]
        )
        from faebryk.library.has_kicad_footprint_equal_ifs import (
            has_kicad_footprint_equal_ifs,
        )

        class _has_kicad_footprint(has_kicad_footprint_equal_ifs):
            @staticmethod
            def get_kicad_footprint() -> str:
                return "Package_DFN_QFN:QFN-{leads}-{ep}EP_{size_x}x{size_y}mm_P{pitch}mm_EP{ep_x}x{ep_y}mm{vias}".format(  # noqa: E501
                    leads=pin_cnt,
                    ep=exposed_thermal_pad_cnt,
                    size_x=size_xy_mm[0],
                    size_y=size_xy_mm[1],
                    pitch=pitch_mm,
                    ep_x=exposed_thermal_pad_dimensions_mm[0],
                    ep_y=exposed_thermal_pad_dimensions_mm[1],
                    vias="_ThermalVias" if has_thermal_vias else "",
                )

        self.add_trait(_has_kicad_footprint())
        self.add_trait(has_equal_pins_in_ifs())
        self.add_trait(can_attach_via_pinmap_equal())
