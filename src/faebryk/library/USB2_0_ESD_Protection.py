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
    usb = L.list_field(2, F.USB2_0)

    vbus_esd_protection: F.TBD[bool]
    data_esd_protection: F.TBD[bool]

    def __preinit__(self):
        self.usb[0].usb_if.buspower.voltage.merge(F.Range(4.75 * P.V, 5.25 * P.V))
        self.usb[0].connect(self.usb[1])
        self.usb[0].usb_if.buspower.connect(self.usb[1].usb_if.buspower)
        self.usb[0].usb_if.buspower.decoupled.decouple()

    no_pick: has_part_picked_remove

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.usb[0].usb_if.d, self.usb[1].usb_if.d)

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )
