# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class XT30PW2plus2(Module):
    """
    XT30 connector with 2 high current and 2 low current pins.
    90 degree orientation PCB mount.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power: F.ElectricPower
    contact = L.list_field(2, F.Electrical)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.J
    )
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Changzhou Amass Elec",
            DescriptiveProperties.partno: "XT30PW(2+2)-M.G.B",
        }
    )
    lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C19268030"})
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2401121133_Changzhou-Amass-Elec-XT30-2-2PW-M-G-B_C19268030.pdf"
    )

    @L.rt_field
    def attach_via_pinmap(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power.hv,
                "2": self.power.lv,
                "3": self.contact[0],
                "4": self.contact[1],
            }
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        pass
