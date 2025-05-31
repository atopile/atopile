# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
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
    explicit_part = L.f_field(F.has_explicit_part.by_supplier)("C2827654")

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.usb[0].usb_if.buspower.lv: ["GND"],
                self.usb[0].usb_if.d.n.line: ["IO1"],
                self.usb[0].usb_if.d.p.line: ["IO2"],
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
        self.data_esd_protection.alias_is(True)
        self.vbus_esd_protection.alias_is(True)
