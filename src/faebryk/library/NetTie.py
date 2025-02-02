# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import StrEnum

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class NetTie[T: ModuleInterface](Module):
    class PadType(StrEnum):
        SMD = "SMD"
        THT = "THT"

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.JP
    )
    picked: F.has_part_removed

    # TODO: generate the kicad footprint instead of loading it
    @L.rt_field
    def footprint(self):
        width_mm = f"{self._width:.1f}mm"
        if width_mm not in ["0.5mm", "2.0mm"]:
            raise ValueError(
                f"Width [{width_mm}] is currently not supported for NetTie"
            )

        if self._pin_count < 2 or self._pin_count > 4:
            raise ValueError(
                f"Pin count [{self._pin_count}] is currently not supported for NetTie"
            )

        fp = F.KicadFootprint(pin_names=[f"{i+1}" for i in range(self._pin_count)])
        fp.add(
            F.KicadFootprint.has_kicad_identifier(
                f"NetTie:NetTie-{self._pin_count}_{self._pad_type}_Pad{self._pin_count}"
            )
        )
        return F.has_footprint_defined(fp)

    def __init__(
        self,
        width: float,
        pin_count: int = 2,
        pad_type: PadType = PadType.SMD,
        interface_type: type[T] = F.Electrical,
    ) -> None:
        super().__init__()
        self._width = width
        self._pin_count = pin_count
        self._pad_type = pad_type
        self._interface_type = interface_type

    def __preinit__(self):
        unnamed = L.list_field(self._pin_count, self._interface_type)
        self.add(unnamed, "unnamed")

        if self._pin_count == 2:
            self.add(F.can_bridge_defined(*unnamed))
