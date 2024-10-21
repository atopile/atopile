# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class TECH_PUBLIC_USBLC6_2SC6(F.USB2_0_ESD_Protection):
    """
    USB 2.0 ESD protection

    6A 12V 150W 6V Unidirectional 5V SOT-23-6 ESD and Surge Protection (TVS/ESD) ROHS
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C2827654"})
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "TECH PUBLIC",
            DescriptiveProperties.partno: "USBLC6-2SC6",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.lcsc.com/datasheet/lcsc_datasheet_2108132230_TECH-PUBLIC-USBLC6-2SC6_C2827654.pdf"
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.usb[0].usb_if.buspower.lv: ["GND"],
                self.usb[0].usb_if.d.n.signal: ["IO1"],
                self.usb[0].usb_if.d.p.signal: ["IO2"],
                self.usb[0].usb_if.buspower.hv: ["VBUS"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        pass
