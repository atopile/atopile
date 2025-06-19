# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class QWIIC_Connector(Module):
    """
    SparkFun's Qwiic Connect System uses 4-pin JST connectors to quickly interface
    development boards with sensors, LCDs, relays and more via I2C.
    1x4P 4P JST SH 1mm pitch horizontal mount
    """

    power: F.ElectricPower
    i2c: F.I2C

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.X
    )
    explicit_part = L.f_field(F.has_explicit_part.by_mfr)(
        "JST Sales America", "SM04B-SRSS-TB(LF)(SN)"
    )
    datasheet = L.f_field(F.has_datasheet_defined)("https://www.sparkfun.com/qwiic")

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power.lv: ["1"],
                self.power.lv: ["2"],
                self.i2c.sda.line: ["3"],
                self.i2c.scl.line: ["4"],
                # n.c. ["5"],
                # n.c. ["6"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power.lv,
                "2": self.power.hv,
                "3": self.i2c.sda.line,
                "4": self.i2c.scl.line,
            }
        )

    def __preinit__(self):
        self.power.voltage.constrain_subset(L.Range.from_center(3.3 * P.V, 0.3 * P.V))
        # self.power.max_current.constrain_subset(
        #    L.Range.from_center_rel(226 * P.mA, 0.05)
        # )
