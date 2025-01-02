# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import StrEnum

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.iso_metric_screw_thread import Iso262_MetricScrewThreadSizes
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class Mounting_Hole(Module):
    class PadType(StrEnum):
        NoPad = ""
        Pad = "Pad"
        Pad_TopBottom = "Pad_TopBottom"
        Pad_TopOnly = "Pad_TopOnly"
        Pad_Via = "Pad_Via"

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.H
    )

    def __init__(self, diameter: Iso262_MetricScrewThreadSizes, pad_type: PadType):
        super().__init__()
        self._diameter = diameter
        self._pad_type = pad_type

    @L.rt_field
    def footprint(self):
        size_mm = f"{self._diameter.value:.1f}mm"
        size_name = self._diameter.name.replace("_", ".")
        padtype = self._pad_type

        if size_name:
            size_name = f"_{size_name}"
        if padtype:
            padtype = f"_{padtype}"

        return F.has_footprint_defined(
            F.KicadFootprint(
                f"MountingHole:MountingHole_{size_mm}{size_name}{padtype}",
                pin_names=[],
            )
        )
