# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import StrEnum

import faebryk.library._F as F
from atopile.errors import UserBadParameterError
from faebryk.core.module import Module
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class TestPoint(Module):
    """
    A PCB test point.
    Currently supporting Loop and Pad (square/circular) types
    """

    class PadType(StrEnum):
        DOUBLE_PAD = "2Pads"
        BRIDGE = "Bridge"
        KEYSTONE = "Keystone"
        LOOP = "Loop"
        PLATED_HOLE = "Plated_Hole"
        PAD_ROUND = "Pad_Round"
        PAD_SQUARE = "Pad_Square"
        THROUGH_HOLE = "THTPad"

    contact: F.Electrical

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.TP
    )
    picked: F.has_part_removed

    # TODO: generate the kicad footprint instead of loading it
    @L.rt_field
    def footprint(self):
        fp = F.KicadFootprint(pin_names=["1"])

        if self._pad_type == self.PadType.LOOP:
            valid_loop_sizes = [
                ("1.80", "1.0"),
                ("2.50", "1.0"),
                ("2.50", "1.85"),
                ("2.54", "1.5"),
                ("2.60", "0.9"),
                ("2.60", "1.4"),
                ("2.60", "1.6"),
                ("3.50", "0.9"),
                ("3.50", "1.4"),
                ("3.80", "1.4"),
                ("3.80", "2.5"),
                ("3.80", "2.8"),
            ]
            diameter = f"{self._diameter:.2f}"
            drill = f"{self._drill_diameter:.1f}"
            if (diameter, drill) not in valid_loop_sizes:
                raise ValueError(
                    f"Diameter [{diameter}] and drill diameter [{drill}] is currently not supported for Loop type TestPoint"  # noqa: E501
                )
            pad_size = f"D{diameter}mm_{drill}mm_{self._beaded}"
            pad_name = self._pad_type.value
        elif (
            self._pad_type == self.PadType.PAD_ROUND
            or self._pad_type == self.PadType.PAD_SQUARE
        ):
            valid_pad_sizes = [
                "1.0",
                "1.5",
                "2.0",
                "2.5",
                "3.0",
                "4.0",
            ]
            size = f"{self._size:.1f}"
            if size not in valid_pad_sizes:
                raise ValueError(
                    f"Size [{size}] is currently not supported for Pad type TestPoint"  # noqa: E501
                )
            if self._pad_type == self.PadType.PAD_SQUARE:
                pad_size = f"{size}x{size}mm"
            elif self._pad_type == self.PadType.PAD_ROUND:
                pad_size = f"D{self._size}mm"
            pad_name = self._pad_type.value.split("_")[0]
        fp.add(
            F.KicadFootprint.has_kicad_identifier(
                f"TestPoint:TestPoint_{pad_name}_{pad_size}"
            )
        )
        return F.has_footprint_defined(fp)

    def __init__(
        self,
        beaded: bool = True,
        drill_diameter: float = 2.54,
        diameter: float = 1.5,
        size: float = 1.0,
        pad_type: PadType = PadType.PAD_ROUND,
    ) -> None:
        super().__init__()
        self._size = size
        self._beaded = beaded
        self._drill_diameter = drill_diameter
        self._diameter = diameter
        self._pad_type = pad_type

    def __preinit__(self):
        if self._pad_type not in [
            self.PadType.LOOP,
            self.PadType.PAD_ROUND,
            self.PadType.PAD_SQUARE,
        ]:
            raise UserBadParameterError(
                "Only Loop and (circular/square) Pad pad-types are supported"
            )

        # connect to footprint
        self.footprint.get_footprint().get_trait(F.can_attach_via_pinmap).attach(
            pinmap={"1": self.contact}
        )
