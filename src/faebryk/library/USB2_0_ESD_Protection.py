# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.picker.picker import has_part_picked_remove
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


# TODO this seems like it should be doing more
class USB2_0_ESD_Protection(Module):
    """
    USB 2.0 ESD protection
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    usb = L.list_field(2, F.USB2_0)

    vbus_esd_protection: F.TBD
    data_esd_protection: F.TBD

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.usb[0], self.usb[1])

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        self.usb[0].connect(self.usb[1])
        self.usb[0].usb_if.buspower.decoupled.decouple()

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.usb[0].usb_if.buspower.voltage.merge(F.Range(4.75 * P.V, 5.25 * P.V))

        # TODO remove if adding any child modules
        has_part_picked_remove.mark_no_pick_needed(self)
