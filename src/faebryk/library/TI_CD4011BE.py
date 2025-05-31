# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.libs.library import L


class TI_CD4011BE(F.CD4011):
    # footprint = L.f_field(F.has_footprint_defined)(
    #    F.DIP(pin_cnt=14, spacing=7.62 * P.mm, long_pads=False)
    # )

    @L.rt_field
    def can_attach(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "7": self.power.lv,
                "14": self.power.hv,
                "3": self.gates[0].outputs[0].line,
                "4": self.gates[1].outputs[0].line,
                "11": self.gates[2].outputs[0].line,
                "10": self.gates[3].outputs[0].line,
                "1": self.gates[0].inputs[0].line,
                "2": self.gates[0].inputs[1].line,
                "5": self.gates[1].inputs[0].line,
                "6": self.gates[1].inputs[1].line,
                "12": self.gates[2].inputs[0].line,
                "13": self.gates[2].inputs[1].line,
                "9": self.gates[3].inputs[0].line,
                "8": self.gates[3].inputs[1].line,
            }
        )

    mfn_pn = L.f_field(F.has_explicit_part.by_mfr)("Texas Instruments", "CD4011BE")
