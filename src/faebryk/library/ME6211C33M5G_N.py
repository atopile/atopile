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
        self.output_voltage.constrain_superset(L.Range.from_center_rel(3.3 * P.V, 0.02))

        if self._default_enabled:
            self.enable.set(True)

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power_in.hv,
                "2": self.power_in.lv,
                "3": self.enable.get_enable_signal(),
                "5": self.power_out.hv,
            }
        )

    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C82942")
