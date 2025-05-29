# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class Winbond_Elec_W25Q128JVSIQ(F.SPIFlash):
    """
    TODO: Docstring describing your module

    128Mbit SOIC-8-208mil
    NOR FLASH ROHS
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    # ----------------------------------------
    #                 traits
    # ----------------------------------------

    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C97521")

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.qspi.chip_select.line: ["CS#", "~{CS}"],
                self.qspi.data[0].line: ["DO"],
                self.qspi.data[2].line: ["IO2"],
                self.power.lv: ["GND"],
                self.qspi.data[1].line: ["DI"],
                self.qspi.clock.line: ["CLK"],
                self.qspi.data[3].line: ["IO3"],
                self.power.hv: ["VCC"],
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
        pass
