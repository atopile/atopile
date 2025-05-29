# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class Winbond_W25Q16JVUXIQ(F.SPIFlash):
    """
    16Mbit USON-8-EP(2x3) NOR FLASH ROHS
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    explicit_part = L.f_field(F.has_explicit_part.by_mfr)("Winbond", "W25Q16JVUXIQ")

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.qspi.clock.line: ["CLK"],
                self.qspi.chip_select.line: ["CS#", "~{CS}"],
                self.qspi.data[0].line: ["DI(IO0)"],
                self.qspi.data[1].line: ["DO(IO1)"],
                self.power.lv: ["GND", "EP"],
                self.qspi.data[3].line: ["HOLD#orRESET#(IO3)"],
                self.power.hv: ["VCC"],
                self.qspi.data[2].line: ["WP#(IO2)"],
            },
            accept_prefix=True,
            case_sensitive=False,
        )

    @L.rt_field
    def decoupled(self):
        return F.can_be_decoupled_rails(self.power)

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        (self.memory_size <= 16 * P.Mbit).constrain()

        self.power.voltage.constrain_subset(L.Range(2.7 * P.V, 3.6 * P.V))
