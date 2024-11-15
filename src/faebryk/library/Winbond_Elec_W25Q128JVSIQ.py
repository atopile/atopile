# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
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
    lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C97521"})
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Winbond Elec",
            DescriptiveProperties.partno: "W25Q128JVSIQ",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1811142111_Winbond-Elec-W25Q128JVSIQ_C97521.pdf"
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.qspi.chip_select.signal: ["CS#"],
                self.qspi.data[0].signal: ["DO"],
                self.qspi.data[2].signal: ["IO2"],
                self.power.lv: ["GND"],
                self.qspi.data[1].signal: ["DI"],
                self.qspi.clock.signal: ["CLK"],
                self.qspi.data[3].signal: ["IO3"],
                self.power.hv: ["VCC"],
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
        pass
