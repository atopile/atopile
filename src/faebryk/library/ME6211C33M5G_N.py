# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.units import P


class ME6211C33M5G_N(F.LDO):
    """
    3.3V 600mA LDO
    """

    # components

    def __init__(self, default_enabled: bool = True) -> None:
        super().__init__()
        self._default_enabled = default_enabled

    def __preinit__(self):
        # set constraints
        self.output_voltage.merge(F.Range(3.3 * 0.98 * P.V, 3.3 * 1.02 * P.V))

        if self._default_enabled:
            self.enable.set(True)

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("U")

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power_in.hv,
                "2": self.power_in.lv,
                "3": self.enable,
                "5": self.power_out.hv,
            }
        )

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://datasheet.lcsc.com/lcsc/1811131510_MICRONE-Nanjing-Micro-One-Elec-ME6211C33M5G-N_C82942.pdf"
    )
