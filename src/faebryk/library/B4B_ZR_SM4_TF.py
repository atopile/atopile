# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
import faebryk.libs.library.L as L
from faebryk.core.module import Module


class B4B_ZR_SM4_TF(Module):
    pin = L.list_field(4, F.Electrical)
    mount = L.list_field(2, F.Electrical)

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2304140030_BOOMELE-Boom-Precision-Elec-1-5-4P_C145997.pdf"
    )
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.J
    )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.pin[0],
                "2": self.pin[1],
                "3": self.pin[2],
                "4": self.pin[3],
                "5": self.mount[0],
                "6": self.mount[1],
            }
        )
