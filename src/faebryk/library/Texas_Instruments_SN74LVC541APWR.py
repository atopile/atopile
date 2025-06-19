# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class Texas_Instruments_SN74LVC541APWR(F.SNx4LVC541A):
    """
    Octal buffer/driver for 1.65-V to 3.6-V VCC operation
    """

    # ----------------------------------------
    #                traits
    # ----------------------------------------
    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C113281")
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.ti.com/lit/ds/symlink/sn74lvc541a.pdf"
    )

    @L.rt_field
    def attach_via_pinmap(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.output_enable[0].line,
                "2": self.A[0].line,
                "3": self.A[1].line,
                "4": self.A[2].line,
                "5": self.A[3].line,
                "6": self.A[4].line,
                "7": self.A[5].line,
                "8": self.A[6].line,
                "9": self.A[7].line,
                "10": self.power.lv,
                "11": self.Y[0].line,
                "12": self.Y[1].line,
                "13": self.Y[2].line,
                "14": self.Y[3].line,
                "15": self.Y[4].line,
                "16": self.Y[5].line,
                "17": self.Y[6].line,
                "18": self.Y[7].line,
                "19": self.output_enable[1].line,
                "20": self.power.hv,
            }
        )

    def __preinit__(self):
        pass
