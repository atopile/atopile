# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum
from pathlib import Path

import faebryk.library._F as F
from atopile.errors import UserBadParameterError
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.part_lifecycle import PartLifecycle

logger = logging.getLogger(__name__)


class TestPoint(Module):
    """
    Basic test point.
    """

    class PadShape(Enum):
        ROUND = "Round"
        SQUARE = "Square"

    class PadType(Enum):
        SMD = "Pad"
        THT = "THTPad"

    contact: F.Electrical

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    picked: F.has_part_removed

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.TP
    )

    def footprint_name(self) -> str:
        # e.g. TestPoint_THTPad_1.0x1.0mm_Drill0.5mm
        # Map pad size (outer diameter / side length) to recommended drill diameter
        # (both in mm)
        supported_pad_sizes_drill_diameters: dict[float, float] = {
            1.0: 0.5,
            1.5: 0.7,
            2.0: 1.0,
            2.5: 1.2,
            3.0: 1.5,
            4.0: 2.0,
        }

        if self._size not in supported_pad_sizes_drill_diameters:
            supported_sizes = ", ".join(
                str(size) for size in supported_pad_sizes_drill_diameters
            )
            raise UserBadParameterError(
                f"Size [{self._size}] is currently not supported for TestPoints. "
                f"Supported sizes are: [{supported_sizes}]."
            )

        pad_size = f"D{self._size:.1f}mm"
        if self._pad_shape == self.PadShape.SQUARE:
            pad_size = f"{self._size:.1f}x{self._size:.1f}mm"

        drill_diameter = ""
        if self._pad_type == self.PadType.THT:
            drill_diameter = (
                f"_Drill{supported_pad_sizes_drill_diameters[self._size]}mm"
            )

        return f"TestPoint_{self._pad_type.value}_{pad_size}{drill_diameter}"

    def __init__(
        self,
        size: float = 1.0,
        pad_shape: PadShape = PadShape.ROUND,
        pad_type: PadType = PadType.SMD,
    ) -> None:
        super().__init__()
        self._size = size
        if isinstance(pad_shape, str):
            pad_shape = self.PadShape[pad_shape]
        self._pad_shape = pad_shape
        if isinstance(pad_type, str):
            pad_type = self.PadType[pad_type]
        self._pad_type = pad_type

    def __preinit__(self):
        # add footprint
        fp_name = self.footprint_name()
        fp_lib_name = "TestPoint"
        fp_dir = Path(__file__).parent / "footprints" / fp_lib_name
        fp_path = fp_dir / f"{fp_name}.kicad_mod"

        fp = F.KicadFootprint.from_path(fp_path, lib_name=fp_lib_name)
        self.get_trait(F.can_attach_to_footprint).attach(fp)

        lifecycle = PartLifecycle.singleton()
        lifecycle.library._insert_fp_lib(fp_lib_name, fp_dir)

        # connect to footprint
        fp.get_trait(F.can_attach_via_pinmap).attach(pinmap={"1": self.contact})
        self.contact.add(F.requires_external_usage())

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        #pragma experiment("MODULE_TEMPLATING")
        from "TestPoint.py" import TestPoint

        module Usage:
            basic_testpoint = new TestPoints
            basic_tht_testpoint = new TestPoint<pad_type="THT">
            big_smd_testpoint = new TestPoint<size=3.0, pad_type="SMD">
            medium_tht_testpoint = new TestPoint<size=2.5, pad_type="THT">
            square_smd_testpoint = new TestPoint<size=2.0, pad_shape="SQUARE", pad_type="SMD">

            basic_testpoint.contact ~ basic_tht_testpoint.contact
            big_smd_testpoint.contact ~ medium_tht_testpoint.contact
            basic_testpoint.contact ~ square_smd_testpoint.contact
        """,
        language=F.has_usage_example.Language.ato,
    )
