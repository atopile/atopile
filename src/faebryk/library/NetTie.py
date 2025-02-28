# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import StrEnum

import faebryk.library._F as F
from atopile.errors import UserBadParameterError
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class NetTie(Module):
    """A net tie component that can bridge different interfaces."""

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
        supported_widths = ["0.5mm", "2.0mm"]
        if width_mm not in supported_widths:
            raise ValueError(
                f"Width [{width_mm}] is currently not supported for NetTie. Supported widths are: {supported_widths}"  # noqa: E501
            )

        if self._pin_count < 2 or self._pin_count > 4:
            raise ValueError(
                f"Pin count [{self._pin_count}] is currently not supported for NetTie"
            )

        fp = F.KicadFootprint(pin_names=[f"{i+1}" for i in range(self._pin_count)])
        fp.add(
            F.KicadFootprint.has_kicad_identifier(
                f"NetTie:NetTie-{self._pin_count}_{self._pad_type}_Pad{width_mm}"
            )
        )
        return F.has_footprint_defined(fp)

    @L.rt_field
    def power(self):
        return times(self._pin_count, F.ElectricPower)

    def __init__(
        self,
        width: float = 0.5,
        pin_count: int = 2,
        pad_type: PadType = PadType.SMD,
        connect_gnd: bool = True,
    ) -> None:
        super().__init__()
        self._width = width
        self._pin_count = pin_count
        self._pad_type = pad_type
        self._connect_gnd = connect_gnd

    def __preinit__(self):
        if self._pin_count == 1:
            raise UserBadParameterError("NetTie with <2 pins is not allowed")

        if self._pin_count == 2:
            self.add(F.can_bridge_defined(*self.power))

        # Connect all interfaces to the first one
        for p in self.power[1:]:
            p.connect_shallow(self.power[0])

        # connect to footprint
        self.footprint.get_footprint().get_trait(F.can_attach_via_pinmap).attach(
            pinmap={
                f"{i+1}": power.lv if self._connect_gnd else power.hv
                for i, power in enumerate(self.power)
            }
        )
