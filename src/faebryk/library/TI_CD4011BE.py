# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.libs.library import L
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P


class TI_CD4011BE(F.CD4011):
    footprint = L.f_field(F.has_footprint_defined)(
        F.DIP(pin_cnt=14, spacing=7.62 * P.mm, long_pads=False)
    )

    def __preinit__(self):
        self.footprint.get_footprint().get_trait(F.can_attach_via_pinmap).attach(
            {
                "7": self.power.lv,
                "14": self.power.hv,
                "3": self.gates[0].outputs[0].signal,
                "4": self.gates[1].outputs[0].signal,
                "11": self.gates[2].outputs[0].signal,
                "10": self.gates[3].outputs[0].signal,
                "1": self.gates[0].inputs[0].signal,
                "2": self.gates[0].inputs[1].signal,
                "5": self.gates[1].inputs[0].signal,
                "6": self.gates[1].inputs[1].signal,
                "12": self.gates[2].inputs[0].signal,
                "13": self.gates[2].inputs[1].signal,
                "9": self.gates[3].inputs[0].signal,
                "8": self.gates[3].inputs[1].signal,
            }
        )

        self.add(
            F.has_descriptive_properties_defined(
                {
                    DescriptiveProperties.manufacturer: "Texas Instruments",
                    DescriptiveProperties.partno: "CD4011BE",
                },
            )
        )
