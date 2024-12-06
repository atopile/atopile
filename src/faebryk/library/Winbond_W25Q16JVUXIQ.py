# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
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
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Winbond",
            DescriptiveProperties.partno: "W25Q16JVUXIQ",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.lcsc.com/datasheet/lcsc_datasheet_2205122030_Winbond-Elec-W25Q16JVUXIQ_C2843335.pdf"
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.qspi.clock.signal: ["CLK"],
                self.qspi.chip_select.signal: ["CS#"],
                self.qspi.data[0].signal: ["DI(IO0)"],
                self.qspi.data[1].signal: ["DO(IO1)"],
                self.power.lv: ["GND", "EP"],
                self.qspi.data[3].signal: ["HOLD#orRESET#(IO3)"],
                self.power.hv: ["VCC"],
                self.qspi.data[2].signal: ["WP#(IO2)"],
            },
            accept_prefix=False,
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
        (self.memory_size < 16 * P.Mbit).constrain()

        self.power.voltage.constrain_subset(L.Range(2.7 * P.V, 3.6 * P.V))
